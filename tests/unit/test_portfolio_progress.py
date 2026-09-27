import asyncio
import json
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend import portfolio_runtime as module
from backend.portfolio_progress import PortfolioProgress, request_phase, request_label
from backend.portfolio_roles import ALLOCATOR_ROLES
from backend.portfolio_runtime import PortfolioRuntime, business_data


async def query(runtime, client, batch=1):
    prompt = {"task": f"Review source support / batch {batch}", "required_schema": {"answer": "string"}}
    return await runtime.query(client, 'test/model', [{"role": "user", "content": json.dumps(prompt)}],
                               parser=json.loads, validator=lambda value, _: [] if value.get('answer') else ['Missing answer'])


def test_large_phase_reports_batches_retries_and_facts_not_overall_percentage():
    progress = PortfolioProgress()
    progress.plan('source_review', 67, facts=529)
    for index in range(67):
        progress.register(str(index), 'source_review', f'Batch {index + 1}', 'test/model')
        progress.update(str(index), status='complete' if index < 50 else 'running' if index < 54 else 'queued',
                        attempt=2 if index >= 58 else 1)
    snapshot = progress.snapshot()
    assert snapshot['message'] == 'Checking facts against sources: 50/67 batches saved; 4 running; 13 queued (9 retries)'
    assert snapshot['phases'][0]['facts'] == 529
    assert len(snapshot['active_requests']) == 4
    assert len(snapshot['queued_requests']) == 8 and snapshot['queued_count'] == 13
    assert 'progress_pct' not in snapshot
    assert all(row['attempt'] == 2 for row in snapshot['queued_requests'])
    assert len(json.dumps(snapshot)) < 64000


def test_followup_is_separate_and_unplanned_phases_are_not_invented():
    progress = PortfolioProgress()
    progress.plan('research', 3, group='macro')
    progress.plan('research', 3, group='sector')
    progress.plan('research', 3, group='coverage')
    progress.scope = 'followup'
    progress.plan('research', 3)
    phases = progress.snapshot()['phases']
    assert [(row['id'], row['total']) for row in phases] == [('research', 9), ('followup.research', 3)]
    progress.status = 'failed'
    assert not progress.snapshot()['active_requests']


@pytest.mark.parametrize('prompt,expected', [
    ({'task': 'Extract source-linked facts: macro / batch 1'}, 'extraction'),
    ({'task': 'Build source-grounded portfolio evidence: macro'}, 'briefs'),
    ({'task': 'Review source support / batch 1'}, 'source_review'),
    ({'task': 'Reconcile portfolio evidence without losing contrary evidence'}, 'reconciliation'),
    ({'task': 'allocation', 'lane_strategy': 'blind_macro_prior'}, 'macro_prior'),
    ({'task': 'allocation', 'required_schema': {'asset_class_targets': []}}, 'allocators'),
    ({'task': 'Act as the portfolio-positioning judge.'}, 'comparison'),
    ({'task': 'Synthesize three independent portfolio-positioning memos'}, 'synthesis'),
    ({'task': 'Final portfolio investment case / investment details 2'}, 'details'),
    ({'task': 'Explain the recorded portfolio decision without changing it'}, 'commentary'),
])
def test_phase_classification_does_not_modify_model_prompt(prompt, expected):
    original = deepcopy(prompt)
    assert request_phase(prompt, 'pipeline') == expected
    assert prompt == original


def test_progress_uses_the_same_role_names_as_model_routing():
    for role in ALLOCATOR_ROLES:
        assert request_label({'lane_strategy': role['role']}, 'pipeline', 'allocators') == role['label']


@pytest.mark.asyncio
async def test_queue_credit_and_model_time_are_distinct_and_only_results_write(tmp_path, monkeypatch):
    runtime = PortfolioRuntime(tmp_path / 'checkpoint.json', artifact_path=tmp_path / 'run.json')
    writes = []
    original = module.write_json_atomic
    monkeypatch.setattr(module, 'write_json_atomic', lambda *args, **kwargs: (writes.append(args[0]), original(*args, **kwargs))[1])
    runtime.model_slots = asyncio.Semaphore(0)
    credit_started, credit_allowed = asyncio.Event(), asyncio.Event()
    model_started, model_allowed = asyncio.Event(), asyncio.Event()
    class Guard:
        async def call(self, client, *args, **kwargs):
            credit_started.set()
            await credit_allowed.wait()
            return await client(*args, **kwargs)
    runtime.funding_guard = Guard()
    async def client(*args, **kwargs):
        model_started.set()
        await model_allowed.wait()
        return {'content': '{"answer":"saved"}'}
    task = asyncio.create_task(query(runtime, client))
    await asyncio.sleep(0)
    row = next(iter(runtime.progress.tasks.values()))
    assert row['status'] == 'queued' and row['started_at'] is None
    assert not writes
    runtime.model_slots.release()
    await credit_started.wait()
    assert row['status'] == 'checking_credit' and row['started_at'] is None
    credit_allowed.set()
    await model_started.wait()
    assert row['status'] == 'running' and row['started_at'] > row['queued_at']
    assert not writes
    model_allowed.set()
    await task
    assert row['status'] == 'complete'
    saved = json.loads(runtime.checkpoint.read_text())
    assert saved['checkpoint_info']['completed_tasks'] == 1
    assert saved['execution_progress']['phases'][0]['completed'] == 1
    assert runtime.receipts[0]['started_at'] == row['started_at']
    assert writes == [runtime.checkpoint, runtime.artifact_path]


@pytest.mark.asyncio
async def test_response_is_not_marked_saved_until_atomic_write_succeeds(tmp_path, monkeypatch):
    runtime = PortfolioRuntime(tmp_path / 'checkpoint.json')
    runtime.save()
    previous = runtime.checkpoint.read_bytes()
    saved_at = runtime.progress.checkpoint['saved_at']
    def fail(*args):
        assert next(iter(runtime.progress.tasks.values()))['status'] == 'saving'
        raise OSError('Disk unavailable')
    monkeypatch.setattr(runtime, '_write_snapshot', fail)
    with pytest.raises(OSError):
        await query(runtime, AsyncMock(return_value={'content': '{"answer":"received"}'}))
    assert runtime.checkpoint.read_bytes() == previous
    assert runtime.progress.last_result_at
    assert runtime.progress.last_completed_at is None
    assert runtime.progress.checkpoint['status'] == 'failed'
    assert runtime.progress.checkpoint['saved_at'] == saved_at


@pytest.mark.asyncio
async def test_artifact_failure_does_not_misreport_a_successful_checkpoint(tmp_path, monkeypatch):
    runtime = PortfolioRuntime(tmp_path / 'checkpoint.json', artifact_path=tmp_path / 'run.json')
    original = module.write_json_atomic
    def fail_artifact(path, value, **kwargs):
        if path == runtime.artifact_path:
            raise OSError('Artifact write unavailable')
        return original(path, value, **kwargs)
    monkeypatch.setattr(module, 'write_json_atomic', fail_artifact)
    with pytest.raises(module.PortfolioArtifactWriteError):
        await query(runtime, AsyncMock(return_value={'content': '{"answer":"durable"}'}))
    assert json.loads(runtime.checkpoint.read_text())['checkpoint_info']['completed_tasks'] == 1
    assert runtime.progress.checkpoint['status'] == 'saved'
    assert runtime.progress.checkpoint['artifact_status'] == 'failed'
    assert runtime.progress.snapshot()['phases'][0]['completed'] == 1


@pytest.mark.asyncio
async def test_retry_is_visible_and_does_not_inflate_completed_batches(tmp_path, monkeypatch):
    runtime = PortfolioRuntime(tmp_path / 'checkpoint.json')
    events = []
    monkeypatch.setattr(runtime, '_report_progress', lambda: events.append(runtime.progress.snapshot()))
    client = AsyncMock(side_effect=[{'content': '{}'}, {'content': '{"answer":"repaired"}'}])
    await query(runtime, client)
    retry = next(item for event in events for item in event['queued_requests'] if item['attempt'] == 2)
    assert retry['retry_reason'] == 'Completing missing or invalid fields'
    assert runtime.progress.snapshot()['phases'][0]['completed'] == 1
    assert len(runtime.receipts) == 2


@pytest.mark.asyncio
async def test_resume_reuses_saved_output_and_telemetry_never_enters_prompts(tmp_path):
    original = PortfolioRuntime(tmp_path / 'first.json')
    client = AsyncMock(return_value={'content': '{"answer":"saved"}'})
    await query(original, client)
    resumed = PortfolioRuntime(tmp_path / 'resumed.json', original.checkpoint)
    no_call = AsyncMock(side_effect=AssertionError('Must reuse checkpoint'))
    await query(resumed, no_call)
    no_call.assert_not_awaited()
    assert resumed.progress.snapshot()['phases'][0]['reused'] == 1
    assert not resumed.checkpoint.exists(), 'Cache hits must not rewrite the checkpoint'
    data = {'evidence': {'execution_progress': {'secret': 'telemetry'}, 'checkpoint_info': {}, 'facts': [1]}}
    assert business_data(data) == {'evidence': {'facts': [1]}}


@pytest.mark.asyncio
async def test_followup_can_reuse_initial_citation_batch_without_losing_its_progress(tmp_path):
    runtime = PortfolioRuntime(tmp_path / 'checkpoint.json')
    call = AsyncMock(return_value={'results': [{'url': 'https://example.org', 'content': 'Source text'}]})
    inputs = {'urls': ['https://example.org']}
    await runtime.research('citation_source_text', inputs, call)
    runtime.progress.scope = 'followup'
    runtime.plan('source_text', 1)
    await runtime.research('citation_source_text', inputs, call)
    assert call.await_count == 1
    phases = runtime.progress.snapshot()['phases']
    assert [(row['id'], row['completed']) for row in phases] == [('source_text', 1), ('followup.source_text', 1)]
    assert phases[1]['reused'] == 1 and phases[0]['reused'] == 0


@pytest.mark.asyncio
async def test_job_heartbeat_does_not_fake_output_or_checkpoint_progress(monkeypatch):
    from backend.jobs import executor
    job = {'job_id': 'test', 'status': 'running', 'request': {'job_type': 'portfolio_positioning'},
           'last_output_at': 'real output', 'execution_progress': {'checkpoint': {'saved_at': 'real checkpoint'}}}
    monkeypatch.setattr(executor, 'ANALYSIS_JOBS', {'test': job})
    monkeypatch.setattr(executor, '_persist_job_record', lambda _: None)
    process = SimpleNamespace(returncode=None)
    count = 0
    async def tick(_):
        nonlocal count
        count += 1
        if count == 2:
            process.returncode = 0
    monkeypatch.setattr(executor.asyncio, 'sleep', tick)
    await executor._heartbeat_analysis_job(job_id='test', process=process)
    assert job['last_output_at'] == 'real output'
    assert job['execution_progress']['checkpoint']['saved_at'] == 'real checkpoint'
    assert job['heartbeat_count'] == 1 and job['heartbeat_at']


@pytest.mark.asyncio
async def test_job_api_keeps_progress_and_clears_live_claims_on_interruption(monkeypatch):
    from backend.jobs import executor
    job = {'job_id': 'test', 'status': 'running', 'request': {'job_type': 'portfolio_positioning'}}
    monkeypatch.setattr(executor, 'ANALYSIS_JOBS', {'test': job})
    monkeypatch.setattr(executor, '_persist_job_record', lambda _: None)
    event = {'completed_tasks': 50, 'execution_progress': {'revision': 5, 'status': 'running',
        'current_phase': 'source_review', 'message': '50/67 batches saved', 'active_requests': [{'id': 'one'}],
        'queued_requests': [{'id': 'two'}], 'queued_count': 1, 'checkpoint': {'saved_at': 'saved'}}}
    await executor._append_job_stream_line('test', 'stdout_tail', 'portfolio progress: ' + json.dumps(event))
    await executor._append_job_stream_line('test', 'stdout_tail', 'portfolio phase: Gathering macro and market research')
    view = executor._public_job_view(job)
    assert view['stage_message'] == '50/67 batches saved'
    assert view['progress_pct'] is None
    assert view['workload'] == {'completed_tasks': 50}
    job['status'] = 'failed'
    view = executor._public_job_view(job)
    assert view['execution_progress']['status'] == 'interrupted'
    assert not view['execution_progress']['active_requests']
    assert view['execution_progress']['checkpoint']['saved_at'] == 'saved'
    assert job['execution_progress']['status'] == 'running', 'Read views must not mutate stored events'


@pytest.mark.asyncio
async def test_sse_emits_request_changes_even_when_phase_and_heartbeat_are_unchanged(monkeypatch):
    from backend.routers import analysis_jobs
    job = {'job_id': 'test', 'status': 'running', 'request': {'job_type': 'portfolio_positioning'},
           'execution_progress': {'revision': 1, 'status': 'running', 'message': 'Checking sources'}}
    monkeypatch.setattr(analysis_jobs, 'ANALYSIS_JOBS', {'test': job})
    monkeypatch.setattr(analysis_jobs.asyncio, 'sleep', AsyncMock())
    response = await analysis_jobs.stream_analysis_job_events('test')
    stream = response.body_iterator
    first = await anext(stream)
    job['execution_progress']['revision'] = 2
    second = await anext(stream)
    await stream.aclose()
    assert '"revision": 1' in first and '"revision": 2' in second


@pytest.mark.asyncio
async def test_portfolio_job_listing_is_filtered_without_loading_company_artifacts(monkeypatch):
    from backend.routers import analysis_jobs
    jobs = {'portfolio': {'job_id': 'p', 'status': 'running', 'request': {'job_type': 'portfolio_positioning'}},
            'company': {'job_id': 'c', 'status': 'running', 'request': {'job_type': 'company'}}}
    monkeypatch.setattr(analysis_jobs, 'ANALYSIS_JOBS', jobs)
    monkeypatch.setattr(analysis_jobs, 'list_gantt_runs', AsyncMock(side_effect=AssertionError('No company scan')), raising=False)
    result = await analysis_jobs.list_analysis_jobs(job_type='portfolio_positioning')
    assert [row['job_id'] for row in result['jobs']] == ['p']
