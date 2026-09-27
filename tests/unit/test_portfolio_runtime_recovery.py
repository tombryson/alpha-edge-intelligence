import argparse
import asyncio
import json
import threading
import time
from unittest.mock import AsyncMock
from types import SimpleNamespace

import pytest
import httpx

import portfolio_positioning_memo as memo
from backend.portfolio_evidence import validate_stage
from backend.portfolio_runtime import CURRENT_RUNTIME, PortfolioRuntime, digest, write_json_atomic
from backend.portfolio_tasks import evidence_for_analysis, source_batches, fact_review_batches


def messages():
    return [{"role": "user", "content": json.dumps({"task": "Evidence extraction", "required_schema": {"answer": "string"}})}]


async def query(runtime, client, **options):
    return await runtime.query(client, "test/model", messages(), parser=memo._extract_json_object,
                               validator=validate_stage, **options)


@pytest.mark.asyncio
async def test_length_is_not_misreported_as_json_even_when_partial_json_parses():
    runtime = PortfolioRuntime()
    client = AsyncMock(side_effect=[
        {"content": '{"answer":"unfinished"}', "finish_reason": "length", "usage": {"completion_tokens": 12000}},
        {"content": "", "finish_reason": "length", "usage": {"completion_tokens_details": {"reasoning_tokens": 24000}}},
        {"content": '{"answer":"complete"}', "finish_reason": "stop"},
    ])
    result = await query(runtime, client, max_tokens=12000, reasoning_effort="medium")
    assert result["stage_status"] == "complete"
    assert all("max_tokens" not in call.kwargs for call in client.call_args_list)
    assert [receipt["failure_type"] for receipt in runtime.receipts] == ["output_truncated", "output_truncated", ""]
    assert all(message["role"] != "assistant" for message in client.call_args_list[1].args[1])
    assert "unfinished" not in json.dumps(client.call_args_list[1].args[1])
    assert client.call_args_list[1].kwargs["reasoning_effort"] == "low"


@pytest.mark.asyncio
async def test_exhausted_truncation_is_bounded_and_not_cached(tmp_path):
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    client = AsyncMock(return_value={"content": '{"answer":', "finish_reason": "length"})
    result = await query(runtime, client, max_tokens=32000)
    assert result["stage_status"] == "failed"
    assert result["error_type"] == "output_truncated"
    assert "no application output-token limit was sent" in result["error"]
    assert client.await_count == 3
    assert all("max_tokens" not in call.kwargs for call in client.call_args_list)
    assert not runtime.cache
    assert len(json.loads(runtime.checkpoint.read_text())["stage_receipts"]) == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 402, 403, 404])
async def test_permanent_provider_failures_do_not_spend_retries(status):
    client = AsyncMock(return_value={"error": "Provider rejected request", "error_type": "http_error", "error_status": status})
    runtime = PortfolioRuntime()
    result = await query(runtime, client)
    assert client.await_count == 1
    assert result["error"] == "Provider rejected request"
    assert result["error_type"] == "http_error"


@pytest.mark.asyncio
async def test_json_format_fallback_does_not_restore_cap_after_truncation():
    client = AsyncMock(side_effect=[
        {"error": "Unsupported", "error_status": 400, "error_body": "response_format json_object unsupported"},
        {"content": "", "finish_reason": "length"},
        {"content": '{"answer":"done"}'},
    ])
    result = await query(PortfolioRuntime(), client, max_tokens=12000)
    assert result["stage_status"] == "complete"
    assert "response_format" not in client.call_args_list[1].kwargs
    assert all("max_tokens" not in call.kwargs for call in client.call_args_list)


@pytest.mark.asyncio
async def test_repair_valid_json_with_invalid_semantics():
    client = AsyncMock(side_effect=[{"content": '{}'}, {"content": '{"answer":"fixed"}'}])
    runtime = PortfolioRuntime()
    assert (await query(runtime, client))["stage_status"] == "complete"
    assert runtime.receipts[0]["failure_type"] == "semantic_validation"
    assert "Missing required field answer" in client.call_args.args[1][-1]["content"]


@pytest.mark.asyncio
async def test_research_survives_code_change_but_not_changed_inputs(tmp_path):
    path = tmp_path / "checkpoint.json"
    old = PortfolioRuntime(path)
    old.code = {"old": "implementation"}
    provider = AsyncMock(return_value={"research_summary": "saved research"})
    await old.research("web", {"query": "frozen", "model": "m1"}, provider)
    resumed = PortfolioRuntime(tmp_path / "new.json", path)
    assert resumed.code != old.code
    unused = AsyncMock(side_effect=AssertionError("No repeat search"))
    result = await resumed.research("web", {"query": "frozen", "model": "m1"}, unused)
    assert result["research_summary"] == "saved research"
    unused.assert_not_awaited()
    await resumed.research("web", {"query": "different", "model": "m1"}, provider)
    await resumed.research("web", {"query": "frozen", "model": "m2"}, provider)
    assert provider.await_count == 3


@pytest.mark.asyncio
async def test_version_one_checkpoint_can_reuse_frozen_research(tmp_path):
    cutoff = "2026-09-16T03:00:00Z"
    code = {"old.py": "oldhash"}
    inputs = {"query": "frozen"}
    key = digest({"stage": "web", "inputs": inputs, "cutoff": cutoff, "code": code})
    path = tmp_path / "old.checkpoint.json"
    path.write_text(json.dumps({"schema_version": 1, "research_cutoff": cutoff, "stage_cache": {
        key: {"receipt": {"stage": "web", "status": "complete", "input_hash": key}, "result": {"research_summary": "frozen"}}}}))
    (tmp_path / "old.json").write_text(json.dumps({"provenance": {"code_manifest": code}}))
    runtime = PortfolioRuntime(tmp_path / "new.json", path)
    provider = AsyncMock(side_effect=AssertionError("No repeat search"))
    assert (await runtime.research("web", inputs, provider))["research_summary"] == "frozen"
    provider.assert_not_awaited()


@pytest.mark.asyncio
async def test_query_results_cannot_mutate_cached_stage(tmp_path):
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    client = AsyncMock(return_value={"content": '{"answer":"original"}'})
    result = await query(runtime, client)
    result["content"] = "changed by downstream enrichment"
    assert (await query(runtime, client))["content"] == '{"answer": "original"}'
    assert client.await_count == 1


def test_checkpoint_streams_lossless_json_without_whole_document_dumps(tmp_path, monkeypatch):
    path = tmp_path / "checkpoint.json"
    artifact = tmp_path / "artifact.json"
    runtime = PortfolioRuntime(path, artifact_path=artifact)
    runtime.partial["source_text"] = "source \\u20ac \\U0001f4c8".encode().decode("unicode_escape")
    runtime.receipts = [{"stage": "saved", "raw_response": {"content": "original"}}]

    original_dumps = json.dumps
    def forbidden(value, *args, **kwargs):
        assert set(value) == {"completed_tasks", "reused_tasks", "new_model_requests", "retry_requests",
                              "reported_openrouter_usd", "unpriced_model_requests", "new_research_requests", "deferred_research_tasks", "execution_progress"}, "Only the small progress summary may use dumps"
        assert len(original_dumps(value)) < 64000, "Progress events must fit within the subprocess line buffer"
        return original_dumps(value, *args, **kwargs)

    monkeypatch.setattr(json, "dumps", forbidden)
    runtime.save()
    assert json.loads(path.read_text())["partial_artifact"] == runtime.partial
    assert json.loads(artifact.read_text())["stage_receipts"] == runtime.receipts
    assert path.read_bytes().isascii()


def test_failed_streamed_save_preserves_previous_checkpoint(tmp_path):
    path = tmp_path / "checkpoint.json"
    write_json_atomic(path, {"answer": "saved"})
    with pytest.raises(TypeError):
        write_json_atomic(path, {"answer": "new", "invalid": object()})
    assert json.loads(path.read_text()) == {"answer": "saved"}


@pytest.mark.asyncio
async def test_async_checkpoint_does_not_block_network_loop_and_freezes_partial_data(tmp_path, monkeypatch):
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    runtime.partial["nested"] = {"value": "before"}
    started, release = threading.Event(), threading.Event()
    write = runtime._write_snapshot

    def slow_write(*args):
        started.set()
        assert release.wait(2), "Event loop could not run while the writer was busy"
        write(*args)

    monkeypatch.setattr(runtime, "_write_snapshot", slow_write)
    pending = asyncio.create_task(runtime.asave())
    try:
        start = time.monotonic()
        assert await asyncio.wait_for(asyncio.to_thread(started.wait, 1), 1.5)
        assert time.monotonic() - start < 1
        runtime.partial["nested"]["value"] = "after"
    finally:
        release.set()
        await pending
    assert json.loads(runtime.checkpoint.read_text())["partial_artifact"]["nested"]["value"] == "before"
    await runtime.asave()
    assert json.loads(runtime.checkpoint.read_text())["partial_artifact"]["nested"]["value"] == "after"


def test_older_snapshot_cannot_overwrite_newer_checkpoint(tmp_path):
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    runtime.partial["value"] = "old"
    old = runtime._snapshot()
    runtime.partial["value"] = "new"
    new = runtime._snapshot()
    runtime._write_snapshot(*new)
    runtime._write_snapshot(*old)
    assert json.loads(runtime.checkpoint.read_text())["partial_artifact"]["value"] == "new"


@pytest.mark.asyncio
async def test_interrupted_cache_commit_reuses_valid_completed_receipt(tmp_path):
    path = tmp_path / "checkpoint.json"
    old = PortfolioRuntime(path)
    client = AsyncMock(return_value={"content": '{"answer":"saved"}', "finish_reason": "stop"})
    await query(old, client)
    old.cache.clear()
    old.receipts[0].pop("retained_output")
    old.receipts[0].pop("warnings")
    old.save()
    resumed = PortfolioRuntime(resume=path)
    result = await query(resumed, client)
    assert json.loads(result["content"]) == {"answer": "saved"}
    assert resumed.receipts[-1]["reused"]
    assert client.await_count == 1


@pytest.mark.asyncio
async def test_interrupted_code_migration_preserves_untouched_cached_tasks(tmp_path):
    original = tmp_path / "original.json"
    interrupted = tmp_path / "interrupted.json"
    client = AsyncMock(return_value={"content": '{"answer":"saved"}'})
    old = PortfolioRuntime(original)
    old.code = {"version": "old"}
    await query(old, client, reasoning_effort="medium")
    await query(old, client, reasoning_effort="low")
    partial = PortfolioRuntime(interrupted, original)
    partial.code = {"version": "new"}
    await query(partial, client, reasoning_effort="medium")
    partial.update_partial(checkpoint_boundary="interrupted after first cached task")
    resumed = PortfolioRuntime(resume=interrupted)
    resumed.code = {"version": "new"}
    result = await query(resumed, client, reasoning_effort="low")
    assert json.loads(result["content"]) == {"answer": "saved"}
    assert resumed.receipts[-1]["reused"]
    assert client.await_count == 2


@pytest.mark.asyncio
async def test_cache_only_replay_defers_disk_writes_until_a_boundary(tmp_path, monkeypatch):
    from unittest.mock import Mock
    original = tmp_path / "original.json"
    old = PortfolioRuntime(original)
    model = AsyncMock(return_value={"content": '{"answer":"saved"}'})
    research = AsyncMock(return_value={"research_summary": "frozen evidence"})
    await query(old, model)
    await old.research("web", {"query": "frozen"}, research)
    resumed = PortfolioRuntime(tmp_path / "resumed.json", original)
    save = Mock(wraps=resumed.save)
    monkeypatch.setattr(resumed, "save", save)
    await query(resumed, model)
    await resumed.research("web", {"query": "frozen"}, research)
    save.assert_not_called()
    resumed.update_partial(evidence_status="complete")
    save.assert_called_once()
    assert len(json.loads(resumed.checkpoint.read_text())["stage_receipts"]) == 2
    assert model.await_count == research.await_count == 1


def test_source_batches_preserve_entire_long_documents_and_metadata():
    packet = {"as_of": "2026-09-16", "sources": [{"id": f"s{i}", "url": f"https://example.org/{i}",
              "excerpt": "a" * size} for i, size in enumerate([0, 9000, 14000, 72000])]}
    batches = source_batches(packet)
    for batch in batches:
        assert sum(len(row["excerpt"]) for row in batch["sources"]) <= 18000
        assert len(batch["sources"]) <= 4
    for source in packet["sources"]:
        pieces = [row for batch in batches for row in batch["sources"] if row["id"] == source["id"]]
        assert pieces
        covered = set()
        for piece in pieces:
            start = piece["excerpt_offset"]
            assert piece["excerpt"] == source["excerpt"][start:start + len(piece["excerpt"])]
            assert piece["url"] == source["url"]
            covered.update(range(start, start + len(piece["excerpt"])))
        assert len(covered) == len(source["excerpt"])


def test_review_batches_and_analysis_projection_preserve_facts_and_dissent():
    facts = [{"id": f"f{i}", "source_ids": [f"s{i}"], "claim_status": "unresolved"} for i in range(23)]
    packet = {"sources": [{"id": f"s{i}", "excerpt": "original full text", "url": "https://example.org"} for i in range(23)]}
    batches = fact_review_batches(facts, packet)
    assert [len(batch["facts"]) for batch in batches] == [16, 7]
    assert [row for batch in batches for row in batch["facts"]] == facts
    brief = {"facts": facts, "source_packet": packet, "major_disagreements": ["contrary evidence"]}
    projected = evidence_for_analysis(brief)
    assert projected["facts"] == facts
    assert projected["major_disagreements"] == brief["major_disagreements"]
    assert len(projected["sources"]) == 23
    assert "original full text" not in json.dumps(projected)
    assert packet["sources"][0]["excerpt"] == "original full text"


@pytest.mark.asyncio
async def test_failed_extraction_saves_research_and_never_calls_allocators(tmp_path, monkeypatch):
    research = {"research_summary": "Preserved original research", "results": [{"url": "https://example.org", "content": "A source"}]}
    monkeypatch.setattr(memo, "_fetch_xai_macro_environment_summary", AsyncMock(return_value=research))
    monkeypatch.setattr(memo.ParallelSourceProvider, "gather", AsyncMock(return_value=research))
    monkeypatch.setattr(memo, "DEFAULT_DEEP_EVIDENCE_RUNS", 1)
    client = AsyncMock(return_value={"content": '{"facts":', "finish_reason": "length"})
    chairman = AsyncMock(side_effect=AssertionError("No allocation without evidence"))
    monkeypatch.setattr(memo, "query_model", client)
    monkeypatch.setattr(memo, "_run_chairman", chairman)
    context = tmp_path / "context.json"
    context.write_text('{"positions": [], "frozen_company_evidence": []}')
    output = tmp_path / "failed.json"
    args = argparse.Namespace(portfolio_context_file=str(context), query="test", mode="deep", dump_json=str(output), run_label="test", resume_checkpoint=None)
    monkeypatch.setattr(memo, "FundingGuard", lambda: None)
    assert await memo._async_main(args) == 1
    artifact = json.loads(output.read_text())
    chairman.assert_not_awaited()
    assert client.await_count == 3
    assert artifact["pipeline_status"] == "failed"
    assert artifact["analysis_health"]["status"] == "incomplete"
    assert artifact["evidence_runs"][0]["parallel"]["research_summary"] == "Preserved original research"
    assert artifact["stage_receipts"][-1]["failure_type"] == "dependency_failed"
    assert "truncated" in artifact["pipeline_error"]


def test_failure_banner_identifies_model_stage_and_truncation(tmp_path):
    from backend.jobs.executor import _analysis_job_output_error
    path = tmp_path / "run.json"
    path.write_text(json.dumps({"schema_version": 3, "stage_receipts": [
        {"stage": "macro:extract", "input_hash": "s1", "status": "failed", "model": "test/model",
         "finish_reason": "length", "request_settings": {"max_tokens": 24000}, "validation_errors": ["Response was not a JSON object"]}]}))
    error = _analysis_job_output_error(path, {"job_type": "portfolio_positioning"})
    assert "macro:extract [test/model]: Output truncated at 24,000 tokens" in error
    assert "Response was not a JSON object" not in error


@pytest.mark.asyncio
@pytest.mark.parametrize("returncode", [1, -9, -15])
async def test_nonzero_subprocess_exit_preserves_detailed_artifact_error(monkeypatch, tmp_path, returncode):
    from backend.jobs import executor
    output = tmp_path / "failed.json"
    output.write_text(json.dumps({"schema_version": 3, "pipeline_status": "failed", "stage_receipts": [
        {"stage": "macro:extract", "input_hash": "x", "status": "failed", "model": "test/model",
         "finish_reason": "length", "request_settings": {"max_tokens": 48000}}]}))
    fields = AsyncMock(return_value={})
    monkeypatch.setattr(executor, "_set_job_fields", fields)
    monkeypatch.setattr(executor, "_build_analysis_job_env", lambda *_: {})
    monkeypatch.setattr(executor, "_prepare_generated_supplementary_for_job", AsyncMock(return_value=(None, [], {})))
    monkeypatch.setattr(executor, "_heartbeat_analysis_job", AsyncMock())
    monkeypatch.setattr(executor, "_consume_process_stream", AsyncMock())
    process = SimpleNamespace(pid=123, returncode=returncode, wait=AsyncMock(), stdout=None, stderr=None)
    monkeypatch.setattr(executor.asyncio, "create_subprocess_exec", AsyncMock(return_value=process))
    await executor._run_analysis_job(job_id="failed", command=["unused"], output_path=output,
                                     request_payload={"job_type": "portfolio_positioning"})
    final = fields.call_args.kwargs
    assert final["status"] == "failed"
    assert final["returncode"] == returncode
    assert final["run_id"] == "failed.json"
    if returncode == 1:
        assert "test/model" in final["error"] and "48,000" in final["error"]
    else:
        assert ("SIGKILL" if returncode == -9 else "SIGTERM") in final["error"]
        assert "48,000" not in final["error"]
    assert "analysis subprocess failed" not in final["error"]


def test_detail_validator_rejects_added_weights_or_missing_assigned_sleeves():
    prompt = {"required_schema": {"allocation_details": [{"asset_class": "string", "investment_case": {}}]},
              "assigned_allocations": [{"asset_class": "cash"}, {"asset_class": "gold"}]}
    assert validate_stage({"allocation_details": [{"asset_class": "cash", "investment_case": {}}]}, prompt)
    assert validate_stage({"allocation_details": [{"asset_class": asset, "investment_case": {}, "target_pct": 99}
                         for asset in ("cash", "gold")]}, prompt)


@pytest.mark.asyncio
async def test_provider_limit_detail_is_preserved_in_failure():
    client = AsyncMock(return_value={"error": "openrouter_http_400", "error_status": 400,
        "error_body": json.dumps({"error": {"message": "Requested output exceeds this model's maximum"}})})
    result = await query(PortfolioRuntime(), client)
    assert "exceeds this model's maximum" in result["error"]
    client.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    {"error": {"code": 503, "message": "Upstream unavailable"}},
    {"choices": [{"finish_reason": "error", "error": {"code": 503, "message": "Upstream unavailable"}}]},
])
async def test_http_200_provider_error_is_not_reported_as_json_parse_failure(monkeypatch, payload):
    from backend import openrouter
    original_client = httpx.AsyncClient
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    monkeypatch.setattr(openrouter.httpx, "AsyncClient", lambda **kwargs: original_client(transport=transport, **kwargs))
    result = await openrouter.query_model("test/model", messages(), include_error_details=True)
    assert result["error_type"] == "provider_error"
    assert result["error_status"] == 503
    assert result["error_retryable"]
    assert result["error"] == "Upstream unavailable"
    assert await openrouter.query_model("test/model", messages()) is None


@pytest.mark.asyncio
async def test_openrouter_keeps_successful_truncation_metadata(monkeypatch):
    from backend import openrouter
    original_client = httpx.AsyncClient
    payload = {"id": "request-id", "usage": {"completion_tokens": 12000},
               "choices": [{"message": {"content": ""}, "finish_reason": "length"}]}
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    monkeypatch.setattr(openrouter.httpx, "AsyncClient", lambda **kwargs: original_client(transport=transport, **kwargs))
    result = await openrouter.query_model("test/model", messages(), include_error_details=True)
    assert result["finish_reason"] == "length"
    assert result["usage"] == payload["usage"]
    assert result["id"] == "request-id"
    assert "error_type" not in result


@pytest.mark.asyncio
@pytest.mark.parametrize("error_class", [
    httpx.ConnectError, httpx.ConnectTimeout,
])
async def test_transient_openrouter_connection_failure_retries_same_stage(monkeypatch, error_class):
    from backend import openrouter
    original_client = httpx.AsyncClient
    calls = []

    def respond(request):
        calls.append(json.loads(request.content))
        if len(calls) == 1:
            raise error_class("", request=request)
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"answer":"retained"}'}, "finish_reason": "stop"}]})

    transport = httpx.MockTransport(respond)
    monkeypatch.setattr(openrouter.httpx, "AsyncClient", lambda **kwargs: original_client(transport=transport, **kwargs))
    runtime = PortfolioRuntime()
    result = await query(runtime, openrouter.query_model)
    assert result["stage_status"] == "complete"
    assert len(calls) == 2 and calls[0] == calls[1]
    assert runtime.receipts[0]["raw_response"]["error_retryable"] is True
    assert runtime.receipts[-1]["status"] == "complete"


@pytest.mark.asyncio
async def test_invalid_openrouter_protocol_does_not_retry(monkeypatch):
    from backend import openrouter
    original_client = httpx.AsyncClient
    calls = []

    def respond(request):
        calls.append(request)
        raise httpx.UnsupportedProtocol("Unsupported URL scheme", request=request)

    transport = httpx.MockTransport(respond)
    monkeypatch.setattr(openrouter.httpx, "AsyncClient", lambda **kwargs: original_client(transport=transport, **kwargs))
    result = await query(PortfolioRuntime(), openrouter.query_model)
    assert result["stage_status"] == "failed" and len(calls) == 1


@pytest.mark.asyncio
async def test_openrouter_preserves_transport_exception_causes(monkeypatch):
    from backend import openrouter
    original_client = httpx.AsyncClient

    def respond(request):
        raise httpx.ConnectError("", request=request) from TimeoutError("TLS handshake timed out")

    transport = httpx.MockTransport(respond)
    monkeypatch.setattr(openrouter.httpx, "AsyncClient", lambda **kwargs: original_client(transport=transport, **kwargs))
    result = await openrouter.query_model("test/model", [{"role": "user", "content": "test"}], include_error_details=True)
    assert result["error"] == "openrouter_connecterror"
    assert result["error_retryable"] is True
    assert result["error_causes"] == ["TimeoutError: TLS handshake timed out"]


@pytest.mark.asyncio
async def test_underfunded_portfolio_is_repaired_not_silently_normalized():
    prompt = {"task": "Fund portfolio", "required_schema": {"asset_class_targets": [{}]}}
    def allocation(weight):
        return {"content": json.dumps({"asset_class_targets": [{"asset_class": "cash", "min_pct": 0,
                                                               "target_pct": weight, "max_pct": 100}]})}
    client = AsyncMock(side_effect=[allocation(91), allocation(100)])
    runtime = PortfolioRuntime()
    result = await runtime.query(client, "test/model", [{"role": "user", "content": json.dumps(prompt)}],
        parser=memo._extract_json_object, validator=validate_stage)
    assert result["stage_status"] == "complete"
    assert "91.00%" in client.call_args.args[1][-1]["content"]
    assert runtime.receipts[0]["failure_type"] == "semantic_validation"
    assert json.loads(runtime.receipts[0]["raw_response"]["content"])["asset_class_targets"][0]["target_pct"] == 91


@pytest.mark.asyncio
@pytest.mark.parametrize("fail_detail", [False, True])
async def test_allocation_details_are_batched_locked_and_recoverable(monkeypatch, tmp_path, fail_detail):
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    runtime.workflow_version = 1
    token = CURRENT_RUNTIME.set(runtime)
    rows = [{"asset_class": f"asset_{i}", "min_pct": 0, "target_pct": 20 if i == 8 else 10, "max_pct": 100}
            for i in range(9)]
    prompts = []
    broken = fail_detail
    def fixture(template):
        if isinstance(template, dict):
            return {key: fixture(value) for key, value in template.items()}
        return [] if isinstance(template, list) else "unknown"
    async def client(model, messages, **kwargs):
        prompt = json.loads(messages[0]["content"])
        prompts.append(prompt)
        result = fixture(prompt["required_schema"])
        if "allocation_details" in result:
            if broken and prompt["assigned_allocations"][0]["asset_class"] == "asset_4":
                return {"content": '{"allocation_details":', "finish_reason": "length"}
            result["allocation_details"] = [{**fixture(prompt["required_schema"]["allocation_details"][0]),
                                               "asset_class": row["asset_class"]} for row in prompt["assigned_allocations"]]
        else:
            result["asset_class_targets"] = rows
        return {"content": json.dumps(result)}
    monkeypatch.setattr(memo, "query_model", client)
    prompt = {"task": "Portfolio allocation", "required_schema": {"asset_class_targets": [{}]},
              "evidence_brief": {"facts": [], "source_packet": {"sources": [{"id": "s", "excerpt": "RAW DOCUMENT"}]}}}
    try:
        result = await memo._query_stage("test/model", [{"role": "user", "content": json.dumps(prompt)}])
        if fail_detail:
            assert result["stage_status"] == "complete"
            retained = json.loads(result["content"])["asset_class_targets"]
            assert [row["target_pct"] for row in retained] == [row["target_pct"] for row in rows]
            assert result["warnings"]
            assert retained[4]["implementation"]["currency"] is None
            assert retained[0]["implementation"]["currency"] == "unknown"
            completed = len(prompts)
            broken = False
            result = await memo._query_stage("test/model", [{"role": "user", "content": json.dumps(prompt)}])
            assert len(prompts) == completed  # Accepted limitations cannot change the frozen prior on resume.
            assert result["warnings"]
        assert result["stage_status"] == "complete"
        assigned = {p["task"]: p["assigned_allocations"] for p in prompts if p.get("assigned_allocations")}
        assert [len(batch) for batch in assigned.values()] == [4, 4, 1]
        actual = json.loads(result["content"])["asset_class_targets"]
        assert [row["target_pct"] for row in actual] == [row["target_pct"] for row in rows]
        assert all(row["investment_case"] for row in actual)
        assert "RAW DOCUMENT" not in json.dumps(prompts)
        assert "implementation" not in prompts[0]["required_schema"]["asset_class_targets"][0]
    finally:
        CURRENT_RUNTIME.reset(token)
