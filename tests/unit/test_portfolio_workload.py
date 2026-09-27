import asyncio
import json
from copy import deepcopy
from unittest.mock import AsyncMock

import httpx
import pytest

import portfolio_positioning_memo as memo
from backend import portfolio_funding as funding
from backend.portfolio_evidence import FACT_FIELDS, apply_fact_checks, merge_briefs, reusable_fact_checks, validate_stage
from backend.portfolio_roles import ALLOCATOR_ROLES
from backend.portfolio_runtime import PortfolioRuntime, load_record, workload_summary
from backend.portfolio_sources import hydrate_citations, public_url
from backend.portfolio_tasks import evidence_for_analysis


def environment():
    return {**{role['key']: json.dumps({'model': 'test/model'}) for role in ALLOCATOR_ROLES},
            **{f'PORTFOLIO_POSITIONING_{key}': 'test/model' for key in
               ('DEEP_SUMMARY_MODEL', 'DEEP_CHAIRMAN_MODEL', 'SYNTHESIS_MODEL', 'DEEP_COMMENTARY_MODEL')}}


def source_fact():
    packet = {'as_of': '2026-09-16', 'sources': [{'id': 's1', 'excerpt': 'GDP growth 3.1 percent', 'published_at': '2026-09-15'}]}
    fact = {'id': 'f1', 'kind': 'observed_macro', 'metric': 'GDP growth', 'value': 3.1, 'unit': 'percent',
            'currency': 'not_applicable', 'benchmark': 'GDP', 'observed_at': '2026-09-15',
            'published_at': '2026-09-15', 'vintage': 'first', 'source_ids': ['s1'], 'source_excerpt': 'GDP growth 3.1 percent',
            'interpretation': 'Contrary evidence must remain visible'}
    checks = [{'fact_id': 'f1', 'checks': {key: 'unresolved' for key in FACT_FIELDS}, 'reason': 'Source does not establish every field'}]
    return packet, apply_fact_checks([fact], checks, packet)[0]


def test_source_checks_reuse_unknowns_but_not_changed_claims_or_sources():
    packet, fact = source_fact()
    checks, pending = reusable_fact_checks([fact], packet)
    assert len(checks) == 1 and not pending
    assert checks[0]['checks']['currency'] == 'unresolved'
    changed = deepcopy(fact)
    changed['value'] = 4
    assert len(reusable_fact_checks([changed], packet)[1]) == 1
    changed_packet = deepcopy(packet)
    changed_packet['sources'][0]['excerpt'] = 'GDP growth revised to 4 percent'
    assert len(reusable_fact_checks([fact], changed_packet)[1]) == 1


def test_followup_duplicate_preserves_existing_source_review():
    packet, fact = source_fact()
    fresh = deepcopy(fact)
    fresh.pop('claim_review')
    merged = merge_briefs([{'facts': [fact], 'source_packet': packet}, {'facts': [fresh], 'source_packet': packet}])
    assert len(merged['facts']) == 1
    assert len(reusable_fact_checks(merged['facts'], merged['source_packet'])[0]) == 1


def test_compact_projection_preserves_observations_sources_and_dissent():
    packet, fact = source_fact()
    fact['interpretations'] = [fact['interpretation'], 'A competing interpretation']
    original = deepcopy(fact)
    result = evidence_for_analysis({'facts': [fact], 'source_packet': packet, 'major_disagreements': ['Opposing case']})
    projected = result['facts'][0]
    for key in (*FACT_FIELDS, 'id', 'source_ids', 'source_excerpt', 'claim_status', 'verification_issues'):
        assert projected[key] == fact[key]
    assert projected['interpretations'] == [fact['interpretation'], 'A competing interpretation']
    assert projected['claim_review']['checks']['currency'] == 'unresolved'
    assert result['major_disagreements'] == ['Opposing case']
    assert fact == original
    assert evidence_for_analysis(result) == result


@pytest.mark.asyncio
async def test_record_store_preserves_receipts_and_cache_without_rewriting_blobs(tmp_path):
    path = tmp_path / 'run.checkpoint.json'
    runtime = PortfolioRuntime(path, artifact_path=tmp_path / 'run.json', record_store=True)
    prompt = {'task': 'test', 'required_schema': {'answer': 'string'}, 'large_evidence': 'original source ' * 10000}
    client = AsyncMock(return_value={'content': '{"answer":"retained"}'})
    messages = [{'role': 'user', 'content': json.dumps(prompt)}]
    await runtime.query(client, 'test/model', messages, parser=memo._extract_json_object, validator=validate_stage)
    files = {p: p.stat().st_mtime_ns for p in (tmp_path / '.portfolio-records').glob('*.json')}
    runtime.save()
    assert files == {p: p.stat().st_mtime_ns for p in files}
    manifest = json.loads(path.read_text())
    assert manifest['schema_version'] == 3 and path.stat().st_size < 10000
    assert load_record(tmp_path, manifest['stage_receipts'][0])['prompt'] == prompt
    resumed = PortfolioRuntime(tmp_path / 'resumed.checkpoint.json', path, record_store=True)
    await resumed.query(client, 'test/model', messages, parser=memo._extract_json_object, validator=validate_stage)
    assert client.await_count == 1 and resumed.receipts[0]['reused']
    assert resumed.workflow_version == 4


@pytest.mark.parametrize('version', [1, 2])
def test_partial_and_terminal_artifacts_preserve_workflow_for_funding_estimates(tmp_path, version):
    output = tmp_path / 'run.json'
    runtime = PortfolioRuntime(tmp_path / 'run.checkpoint.json', artifact_path=output, record_store=True)
    runtime.workflow_version = version
    runtime.update_partial(pipeline_status='running')
    assert json.loads(output.read_text())['workflow_version'] == version
    runtime.persist_artifact({'pipeline_status': 'awaiting_credit', 'stage_receipts': []})
    assert json.loads(output.read_text())['workflow_version'] == version


def test_record_integrity_and_legacy_workflow(tmp_path):
    path = tmp_path / 'legacy.checkpoint.json'
    path.write_text(json.dumps({'stage_cache': {}, 'stage_receipts': []}))
    assert PortfolioRuntime(resume=path).workflow_version == 1
    with pytest.raises(ValueError):
        load_record(tmp_path, {'record_ref': '../secret'})
    store = tmp_path / '.portfolio-records'
    store.mkdir()
    (store / ('0' * 64 + '.json')).write_text('{}')
    with pytest.raises(ValueError):
        load_record(tmp_path, {'record_ref': '0' * 64})


def test_workload_distinguishes_reuse_attempts_and_reported_cost():
    rows = [{'input_hash': 'a', 'status': 'complete', 'reused': True, 'request_settings': {'max_tokens': 10}},
            {'input_hash': 'b', 'status': 'failed', 'attempt': 1, 'started_at': '1', 'request_settings': {}, 'request_id': 'one'},
            {'input_hash': 'b', 'status': 'complete', 'attempt': 2, 'started_at': '2', 'request_settings': {'max_tokens': 10}, 'request_id': 'two', 'usage': {'cost': 0.1}}]
    rows[1]['request_settings'] = {'max_tokens': 10}
    rows.append(deepcopy(rows[-1]))
    result = workload_summary(rows)
    assert result['completed_tasks'] == 2 and result['reused_tasks'] == 1
    assert result['new_model_requests'] == 2 and result['retry_requests'] == 1
    assert result['reported_openrouter_usd'] == 0.1 and result['unpriced_model_requests'] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('limit,remaining,expected', [(None, None, 8), (20, 3, 3)])
async def test_funding_checks_account_and_key_separately(monkeypatch, limit, remaining, expected):
    original = httpx.AsyncClient
    def respond(request):
        data = {'credits': {'total_credits': 10, 'total_usage': 2},
                'key': {'limit': limit, 'limit_remaining': remaining},
                'models': [{'id': '~test/latest', 'pricing': {'prompt': '0', 'completion': '0'}}]}[request.url.path.rsplit('/', 1)[-1]]
        return httpx.Response(200, json={'data': data})
    monkeypatch.setattr(funding, '_catalog', None)
    monkeypatch.setattr(funding.httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(respond), **kwargs))
    result = await funding.funding_snapshot()
    assert result['available_usd'] == expected
    assert funding.request_cost(result['prices'], '~test/latest', 100, 100) == 0


def test_estimate_preserves_roles_and_subtracts_only_matching_completed_work():
    context = {'asset_classes': [{}] * 12}
    plan = funding.estimate_plan(context, environment())
    assert plan['test/model', 'allocation'] == 12
    assert plan['test/model', 'details'] == 9
    previous = {'workflow_version': 2, 'stage_receipts': [
        {'input_hash': 'a', 'status': 'complete', 'model': 'test/model', 'stage': 'Allocate', 'request_settings': {'max_tokens': 100}},
        {'input_hash': 'b', 'status': 'failed', 'model': 'test/model', 'stage': 'Allocate', 'request_settings': {'max_tokens': 100}}]}
    assert funding.estimate_plan(context, environment(), previous)['test/model', 'allocation'] == 7
    previous['stage_receipts'][0]['model'] = 'changed/model'
    assert funding.estimate_plan(context, environment(), previous)['test/model', 'allocation'] == 8


@pytest.mark.asyncio
async def test_preflight_warns_below_forecast_but_blocks_fixed_charge_and_unknown_prices(monkeypatch):
    snapshot = {'available_usd': 2, 'prices': {'test/model': {'prompt': 0, 'completion': 0, 'request': 0.1}}}
    monkeypatch.setattr(funding, 'funding_snapshot', AsyncMock(return_value=snapshot))
    result = await funding.preflight({}, environment(), reserved_usd=1)
    assert result['status'] == 'ready' and result['available_usd'] == 1
    assert result['top_up_usd'] > 0 and result['low_balance_warning']
    assert (await funding.preflight({}, environment(), reserved_usd=1.95))['status'] == 'insufficient'
    snapshot['prices'] = {}
    assert (await funding.preflight({}, environment()))['status'] == 'unverified'


@pytest.mark.asyncio
async def test_credit_guard_drains_inflight_result_and_retains_resume_checkpoint(monkeypatch, tmp_path):
    monkeypatch.setattr(funding, 'funding_snapshot', AsyncMock(return_value={
        'available_usd': 0.15, 'prices': {'test/model': {'prompt': 0, 'completion': 0, 'request': 0.1}}}))
    runtime = PortfolioRuntime(tmp_path / 'run.checkpoint.json')
    runtime.funding_guard = funding.FundingGuard()
    started, release = asyncio.Event(), asyncio.Event()
    async def client(*args, **kwargs):
        started.set()
        await release.wait()
        return {'content': '{"answer":"saved"}'}
    async def run(task):
        return await runtime.query(client, 'test/model', [{'role': 'user', 'content': json.dumps({'task': task, 'required_schema': {'answer': 'string'}})}],
            parser=memo._extract_json_object, validator=validate_stage)
    first = asyncio.create_task(run('one'))
    await started.wait()
    with pytest.raises(funding.FundingRequired):
        await run('two')
    release.set()
    assert (await first)['stage_status'] == 'complete'
    saved = json.loads(runtime.checkpoint.read_text())
    assert len(saved['stage_cache']) == 1
    assert saved['partial_artifact']['funding']['status'] == 'insufficient'


@pytest.mark.asyncio
async def test_credit_rejection_is_not_converted_into_missing_optional_fields(monkeypatch):
    monkeypatch.setattr(funding, 'funding_snapshot', AsyncMock(return_value={
        'available_usd': 100, 'prices': {'test/model': {'prompt': 0, 'completion': 0}}}))
    client = AsyncMock(return_value={'error_status': 402, 'error': 'No credit'})
    guard = funding.FundingGuard()
    with pytest.raises(funding.FundingRequired):
        await guard.call(client, 'test/model', [])
    with pytest.raises(funding.FundingRequired):
        await guard.call(client, 'test/model', [])
    assert client.await_count == 1


@pytest.mark.asyncio
async def test_citation_text_is_deduplicated_frozen_and_never_replaced_by_summary(monkeypatch, tmp_path):
    source = {'results': [{'url': 'https://example.org/release', 'content': ''}], 'summary': 'Unverified model narrative'}
    lanes = [{'macro_news': source}, {'perplexity': deepcopy(source)}]
    extract = AsyncMock(return_value={'results': [{'url': 'https://example.org/release', 'content': 'Original release text'}]})
    monkeypatch.setattr('backend.portfolio_retrieval.ParallelExtractProvider._run', extract)
    path = tmp_path / 'checkpoint.json'
    runtime = PortfolioRuntime(path)
    await hydrate_citations(lanes, runtime)
    assert extract.await_count == 1 and source['results'][0]['content'] == ''
    assert all(next(iter(lane.values()))['results'][0]['content'] == 'Original release text' for lane in lanes)
    await hydrate_citations([{'macro_news': source}], PortfolioRuntime(resume=path))
    assert extract.await_count == 1


@pytest.mark.asyncio
async def test_missing_citation_text_does_not_discard_other_research(monkeypatch):
    monkeypatch.setattr('backend.portfolio_retrieval.ParallelExtractProvider._run', AsyncMock(side_effect=RuntimeError('Unavailable')))
    lanes = [{'macro_news': {'results': [{'url': 'https://example.org/release', 'content': ''}]}}]
    runtime = PortfolioRuntime()
    await hydrate_citations(lanes, runtime)
    assert lanes[0]['macro_news']['results'][0]['content'] == ''
    assert runtime.receipts[0]['status'] == 'failed' and runtime.receipts[0]['warnings']


@pytest.mark.parametrize('url', ['file:///etc/passwd', 'http://127.0.0.1/x', 'http://localhost/', 'http://a.internal', 'https://user:pass@example.org'])
def test_citation_extraction_rejects_nonpublic_targets(url):
    assert not public_url(url)


@pytest.mark.asyncio
@pytest.mark.parametrize('status,code', [('insufficient', 402), ('unverified', 503)])
async def test_job_preflight_stops_before_creating_files_or_paid_worker(monkeypatch, status, code):
    from fastapi import FastAPI
    from backend.routers import analysis_jobs
    report = {'status': status, 'message': 'Credit check: top up or retry'}
    monkeypatch.setattr(analysis_jobs, '_portfolio_preflight', AsyncMock(return_value=report))
    files, worker = AsyncMock(), AsyncMock()
    monkeypatch.setattr(analysis_jobs, '_store_portfolio_context_for_job', files)
    monkeypatch.setattr(analysis_jobs, '_run_analysis_job', worker)
    app = FastAPI()
    app.include_router(analysis_jobs.router)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://testserver') as client:
        response = await client.post('/api/analysis-jobs', json={'job_type': 'portfolio_positioning', 'portfolio_context': {'asset_classes': []}})
    assert response.status_code == code
    assert response.json()['detail']['message'] == report['message']
    files.assert_not_called()
    worker.assert_not_called()


@pytest.mark.asyncio
async def test_funding_wait_is_saved_as_resumable_work_not_completed_unknown_analysis(tmp_path, monkeypatch):
    context = tmp_path / 'context.json'
    context.write_text(json.dumps({'asset_classes': [{'asset_class': 'cash', 'portfolio_pct': 100}]}))
    monkeypatch.setattr(funding, 'preflight', AsyncMock(return_value={'status': 'insufficient', 'message': 'Add credit; completed work saved'}))
    output = tmp_path / 'run.json'
    from argparse import Namespace
    result = await memo._async_main(Namespace(dump_json=str(output), portfolio_context_file=str(context), query='Original query', resume_checkpoint=None))
    assert result == 75
    artifact = json.loads(output.read_text())
    assert artifact['pipeline_status'] == 'awaiting_credit'
    assert artifact['workflow_version'] == 4
    assert artifact['portfolio_context']['asset_classes'][0]['asset_class'] == 'cash'
    assert artifact['analysis_health']['status'] == 'incomplete'
    assert output.with_suffix('.checkpoint.json').exists()
    assert not artifact['stage_receipts']


def test_portfolio_job_reports_counts_without_a_fictional_percent():
    from backend.jobs.executor import _public_job_view
    result = _public_job_view({'status': 'running', 'stage': 'stage3', 'progress_pct': 88,
        'request': {'job_type': 'portfolio_positioning'}, 'workload': {'new_model_requests': 4}})
    assert result['progress_pct'] is None and result['workload']['new_model_requests'] == 4
