import asyncio
from copy import deepcopy
import json
from unittest.mock import AsyncMock

import httpx
import pytest

import portfolio_positioning_memo as memo
from backend.portfolio_decisions import analysis_health, build_decision
from backend.portfolio_retrieval import ParallelSourceProvider, ParallelExtractProvider, normalize_result, source_key
from backend.portfolio_runtime import CURRENT_RUNTIME, PortfolioRuntime
from backend.portfolio_sources import hydrate_citations


def response_packet(count=1):
    return {"run": {"run_id": "trun_test", "processor": "ultra2x", "status": "completed"}, "output": {
        "content": {"summary": "Generated analysis, not original source text", "question_status": "answered",
            "sources": [{"url": f"https://example.org/{index}", "title": "Release", "published_at": "2026-09-01",
                         "supporting_excerpt": "This generated quotation must not become source text"} for index in range(count)]},
        "basis": [{"field": f"sources.{index}", "citations": [{"url": f"https://example.org/{index}",
                   "excerpts": [f"Original dated observation {index}"]}]} for index in range(count)]}}


def test_normalization_uses_basis_not_model_generated_quotes_and_deduplicates():
    raw = response_packet(7)
    raw["output"]["basis"] *= 2
    result = normalize_result(raw)
    assert len(result["results"]) == 5
    assert result["results"][0]["content"] == "Original dated observation 0"
    assert "generated quotation" not in str(result["results"])
    assert result["raw_response"] == raw
    assert result["provider_metadata"]["returned_sources"] == 7
    assert source_key("https://example.org/0?utm_source=x#fragment") == source_key("https://example.org/0")


def test_unsubstantiated_quotes_stay_empty_and_extraction_cannot_add_other_urls():
    raw = response_packet(2)
    raw["output"]["basis"] = raw["output"]["basis"][1:]
    result = normalize_result(raw, urls=["https://example.org/0"])
    assert len(result["results"]) == 1
    assert result["results"][0]["content"] == ""
    assert result["failed_results"][0]["url"] == "https://example.org/0"


@pytest.mark.asyncio
@pytest.mark.parametrize("processor", ["ultra2x", "ultra4x"])
async def test_durable_task_resumes_gets_without_repeating_paid_post(tmp_path, processor):
    path = tmp_path / "checkpoint.json"
    calls = []
    def handler(request):
        calls.append((request.method, str(request.url)))
        if request.method == "POST":
            assert json.loads(path.read_text())["provider_tasks"]
            body = json.loads(request.content)
            assert body["processor"] == processor
            assert "five" in body["input"]
            assert body["task_spec"]["output_schema"]["type"] == "json"
            return httpx.Response(202, json={"run_id": "trun_test", "status": "queued"})
        if request.url.path.endswith("/result"):
            packet = response_packet()
            packet["run"]["processor"] = processor
            return httpx.Response(200, json=packet)
        return httpx.Response(200, json={"run_id": "trun_test", "status": "completed"})
    transport = httpx.MockTransport(handler)
    first = ParallelSourceProvider(api_key="test", processor=processor, transport=transport, timeout_seconds=0)
    pending = await first.gather(PortfolioRuntime(path), question="Treasury yields and duration risk?", deep_research=True)
    assert pending["resumable"]
    saved = json.loads(path.read_text())
    assert next(iter(saved["provider_tasks"].values()))["run_id"] == "trun_test"
    assert saved["stage_cache"] == {}
    resumed = PortfolioRuntime(path, resume=path)
    second = ParallelSourceProvider(api_key="test", processor=processor, transport=transport, poll_seconds=0)
    result = await second.gather(resumed, question="Treasury yields and duration risk?")
    assert result["results"] and len(resumed.cache) == 1
    assert result["model"] == processor
    assert sum(method == "POST" for method, _ in calls) == 1
    count = len(calls)
    await second.gather(PortfolioRuntime(path, resume=path), question="Treasury yields and duration risk?")
    assert len(calls) == count


@pytest.mark.asyncio
async def test_uncertain_submission_is_never_automatically_repeated(tmp_path):
    path = tmp_path / "checkpoint.json"
    posts = []
    def handler(request):
        posts.append(request)
        raise httpx.ReadTimeout("Response lost", request=request)
    provider = ParallelSourceProvider(api_key="test", processor="ultra2x", transport=httpx.MockTransport(handler))
    first = await provider.gather(PortfolioRuntime(path), question="Gold miner margins versus bullion?")
    assert first["resumable"]
    again = await provider.gather(PortfolioRuntime(path, resume=path), question="Gold miner margins versus bullion?")
    assert "uncertain" in again["error"]
    assert len(posts) == 1


@pytest.mark.asyncio
async def test_each_discovery_is_separate_concurrent_and_checkpointed(tmp_path):
    started = []
    both_started = asyncio.Event()
    async def handler(request):
        if request.method == "POST":
            started.append(json.loads(request.content)["input"])
            if len(started) == 2:
                both_started.set()
            await asyncio.wait_for(both_started.wait(), 1)
            return httpx.Response(202, json={"run_id": "trun_" + str(len(started)), "status": "queued"})
        if request.url.path.endswith("/result"):
            return httpx.Response(200, json=response_packet())
        return httpx.Response(200, json={"status": "completed"})
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    provider = ParallelSourceProvider(api_key="test", processor="ultra2x", transport=httpx.MockTransport(handler), poll_seconds=0)
    results = await asyncio.gather(*(provider.gather(runtime, question=question, deep_research=True) for question in ("Treasury duration risk?", "Gold miner margins?")))
    assert all(result.get("results") for result in results)
    assert len(runtime.cache) == 2 and len(runtime.provider_tasks) == 2


@pytest.mark.asyncio
async def test_duplicate_concurrent_requests_share_one_paid_task(tmp_path):
    posts = []
    async def handler(request):
        if request.method == "POST":
            posts.append(request)
            await asyncio.sleep(0)
            return httpx.Response(202, json={"run_id": "trun_test", "status": "queued"})
        if request.url.path.endswith("/result"):
            return httpx.Response(200, json=response_packet())
        return httpx.Response(200, json={"status": "completed"})
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    provider = ParallelSourceProvider(api_key="test", processor="ultra2x", transport=httpx.MockTransport(handler))
    results = await asyncio.gather(*(provider.gather(runtime, question="Treasury duration risk?", deep_research=True) for _ in range(2)))
    assert len(posts) == 1 and results[0] == results[1]
    assert len(runtime.cache) == 1 and runtime.receipts[-1]["reused"]


@pytest.mark.asyncio
async def test_extraction_keeps_twenty_url_batches_and_reuses_saved_results(tmp_path, monkeypatch):
    calls = []
    async def task(self, runtime, key, settings):
        calls.append(settings)
        return {"results": [{"url": url, "content": "Cited text", "text_provider": "parallel_citation_excerpt"} for url in settings["urls"]]}
    monkeypatch.setattr(ParallelExtractProvider, "_run", task)
    monkeypatch.setattr("backend.portfolio_retrieval.source_processor", lambda: "ultra2x")
    lanes = [{"macro_news": {"results": [{"url": f"https://example.org/{index}", "content": ""} for index in range(22)]}}]
    original = deepcopy(lanes)
    path = tmp_path / "checkpoint.json"
    await hydrate_citations(lanes, PortfolioRuntime(path))
    assert sorted(len(call["urls"]) for call in calls) == [2, 20]
    assert all(row["content"] == "Cited text" for row in lanes[0]["macro_news"]["results"])
    await hydrate_citations(original, PortfolioRuntime(path, resume=path))
    assert len(calls) == 2
    # A different batch still reuses its individual citations, without another task.
    subset = [{"macro_news": {"results": [{"url": "https://example.org/3", "content": ""}]}}]
    await hydrate_citations(subset, PortfolioRuntime(path, resume=path))
    assert len(calls) == 2 and subset[0]["macro_news"]["results"][0]["content"] == "Cited text"


@pytest.mark.asyncio
async def test_known_urls_use_extract_not_deep_research_and_keep_partial_success(tmp_path):
    calls = []
    def handler(request):
        calls.append(request)
        assert request.method == "POST" and request.url.path == "/v1/extract"
        body = json.loads(request.content)
        assert "processor" not in body and "task_spec" not in body
        assert len(body["urls"]) == 2
        return httpx.Response(200, json={"extract_id": "extract_test", "results": [
            {"url": "https://example.org/0", "publish_date": "2026-09-01", "excerpts": ["Original table | 123", "Original table | 123"]},
            {"url": "https://example.org/unrequested", "excerpts": ["Must not enter evidence"]}],
            "errors": [{"url": "https://example.org/1", "message": "Unavailable"}], "usage": [{"count": 2}]})
    provider = ParallelSourceProvider(api_key="test", transport=httpx.MockTransport(handler))
    path = tmp_path / "extract.json"
    result = await provider.gather(PortfolioRuntime(path, record_store=True), urls=["https://example.org/0", "https://example.org/1"])
    assert len(result["results"]) == 1 and result["results"][0]["content"] == "Original table | 123"
    assert result["results"][0]["published_at"] == "2026-09-01"
    assert result["failed_results"][0]["url"] == "https://example.org/1"
    assert result["provider_metadata"]["errors"]
    resumed = PortfolioRuntime(path, resume=path, record_store=True)
    assert await provider.gather(resumed, urls=["https://example.org/0", "https://example.org/1"]) == result
    assert len(calls) == 1 and all("result" not in state for state in resumed.provider_tasks.values())


@pytest.mark.asyncio
async def test_extract_uncertain_post_is_not_repeated(tmp_path):
    calls = []
    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("Lost response", request=request)
    provider = ParallelSourceProvider(api_key="test", transport=httpx.MockTransport(handler))
    path = tmp_path / "uncertain-extract.json"
    first = await provider.gather(PortfolioRuntime(path), urls=["https://example.org/0"])
    assert first["resumable"]
    second = await provider.gather(PortfolioRuntime(path, resume=path), urls=["https://example.org/0"])
    assert "uncertain" in second["error"] and len(calls) == 1


@pytest.mark.asyncio
async def test_extraction_migration_finishes_already_paid_legacy_task(tmp_path):
    runtime = PortfolioRuntime(tmp_path / "legacy-extract.json")
    urls = ["https://example.org/0"]
    settings = {"provider": "parallel", "model": "ultra2x", "question": None, "urls": urls,
        "exclude_urls": [], "max_sources": 5, "contract": 1}
    await runtime.save_provider_task(runtime.research_key("citation_source_text", settings),
        {"run_id": "trun_test", "status": "queued", "processor": "ultra2x"})
    calls = []
    def handler(request):
        calls.append(request)
        assert request.method == "GET" and "/tasks/runs/trun_test" in request.url.path
        return httpx.Response(200, json=response_packet() if request.url.path.endswith("/result") else {"status": "completed"})
    provider = ParallelSourceProvider(api_key="test", processor="ultra4x", transport=httpx.MockTransport(handler))
    result = await provider.gather(runtime, urls=urls)
    assert result["results"][0]["content"] == "Original dated observation 0"
    assert len(calls) == 2


def question(text="What is the Treasury duration sensitivity at current yields?"):
    return {"question": text, "kind": "market_fact", "status": "unanswered", "asset_classes": ["bonds"],
            "material_reason": "Could change the duration of the bond sleeve", "reuse_assessment": "Saved yield levels do not establish duration sensitivity", "existing_fact_ids": ["existing"]}


@pytest.mark.parametrize("updates", [{"status": "answered"}, {"kind": "investor_input"}, {"material_reason": ""},
    {"reuse_assessment": ""}, {"question": "x" * 351}, {"question": '{"portfolio": []}'}])
def test_only_short_material_unanswered_market_questions_can_search(updates):
    assert memo._trade_research_questions({"questions": [{**question(), **updates}]}) == []


def test_missing_fields_are_not_research_and_duplicate_questions_are_grouped():
    assert memo._trade_research_questions({"research_priorities": [{"question": "Investment case missing: horizon months", "trade_size_pct": 30}]}) == []
    assert len(memo._trade_research_questions({"questions": [question(), question()]})) == 1


@pytest.fixture
def followup(monkeypatch, tmp_path):
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    token = CURRENT_RUNTIME.set(runtime)
    baseline = {"evidence_status": "complete", "facts": [{"id": "existing", "metric": "policy rate", "value": 4}],
                "source_packet": {"sources": [{"id": "s1", "url": "https://example.org/existing"}]}}
    monkeypatch.setattr(memo, "_plan_trade_research", AsyncMock(return_value={"questions": [question()]}))
    async def structure(lane, **kwargs):
        lane["evidence_brief"] = {"evidence_status": "complete", "facts": [{"id": lane["label"], "metric": "duration", "value": 7}]}
        return lane
    monkeypatch.setattr(memo, "_structure_evidence_lane", structure)
    async def reconcile(**kwargs):
        return {**baseline, "facts": [fact for brief in kwargs["evidence_briefs"] for fact in brief["facts"]]}
    monkeypatch.setattr(memo, "_run_evidence_reconciliation", AsyncMock(side_effect=reconcile))
    yield runtime, baseline, {"decision": {}, "evidence_brief": baseline, "mode": "deep", "query": "Portfolio query must not go to retrieval", "asset_class_vocabulary": []}
    CURRENT_RUNTIME.reset(token)


@pytest.mark.asyncio
async def test_answered_by_existing_evidence_requires_no_search(monkeypatch, followup):
    _, baseline, args = followup
    monkeypatch.setattr(memo, "_plan_trade_research", AsyncMock(return_value={"questions": [{**question(), "status": "answered"}]}))
    gather = AsyncMock(side_effect=AssertionError("No redundant retrieval"))
    monkeypatch.setattr(ParallelSourceProvider, "gather", gather)
    evidence, runs, report = await memo._run_targeted_research(**args)
    assert evidence == baseline and not runs and report["status"] == "not_needed"
    gather.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [{"error": "HTTP 500", "results": []}, RuntimeError("Retrieval unavailable")])
async def test_supplementary_failure_keeps_baseline_and_qualifies_recommendation(monkeypatch, followup, failure):
    runtime, baseline, args = followup
    gather = AsyncMock(side_effect=failure) if isinstance(failure, Exception) else AsyncMock(return_value=failure)
    monkeypatch.setattr(ParallelSourceProvider, "gather", gather)
    evidence, runs, report = await memo._run_targeted_research(**args)
    assert evidence["evidence_status"] == "complete" and evidence["facts"] == baseline["facts"]
    assert report["status"] == "with_limitations" and report["unresolved"]
    assert runs[0]["supplementary"] and runtime.progress.scope == "initial"
    assert gather.await_count == 1
    decision = build_decision({"portfolio": {"cash_pct": 100}}, {"asset_class_targets": [{"asset_class": "bonds", "target_pct": 100}]}, evidence)
    assert decision["funding"]["rows"][0]["unanswered_market_questions"]


@pytest.mark.asyncio
async def test_expand_only_surviving_gap_and_send_short_questions(monkeypatch, followup):
    _, baseline, args = followup
    first = {"results": [{"url": "https://example.org/new", "content": "Evidence"}], "question_status": "partial",
             "remaining_question": "What is the duration of the benchmark index?", "expansion_query": "Treasury index modified duration?"}
    second = {"results": [{"url": "https://example.org/second", "content": "More evidence"}], "question_status": "answered"}
    gather = AsyncMock(side_effect=[first, second])
    monkeypatch.setattr(ParallelSourceProvider, "gather", gather)
    evidence, runs, report = await memo._run_targeted_research(**args)
    assert report["status"] == "researched" and len(evidence["facts"]) == 2
    assert gather.await_count == 2 and len(runs[0]["searches"]) == 2
    assert gather.await_args_list[0].kwargs["question"] == question()["question"]
    assert "https://example.org/new" in gather.await_args_list[1].kwargs["exclude_urls"]
    assert "Portfolio query" not in json.dumps([call.kwargs for call in gather.await_args_list])
    assert baseline["facts"] == [{"id": "existing", "metric": "policy rate", "value": 4}]


@pytest.mark.asyncio
@pytest.mark.parametrize("raises", [False, True])
async def test_reconciliation_failure_keeps_successful_observations_as_well_as_baseline(monkeypatch, followup, raises):
    _, baseline, args = followup
    monkeypatch.setattr(ParallelSourceProvider, "gather", AsyncMock(return_value={"results": [{"url": "https://example.org/new"}], "question_status": "answered"}))
    failure = AsyncMock(side_effect=RuntimeError("Summary failed")) if raises else AsyncMock(return_value={"evidence_status": "incomplete", "facts": []})
    monkeypatch.setattr(memo, "_run_evidence_reconciliation", failure)
    evidence, _, report = await memo._run_targeted_research(**args)
    assert {row["metric"] for row in evidence["facts"]} == {"policy rate", "duration"}
    assert evidence["evidence_status"] == "complete" and evidence["supplementary_synthesis_status"] == "unreconciled"
    assert report["unresolved"] and report["reconciliation_error"]
    assert report["questions"][0]["status"] == "unanswered"
    assert report["questions"][0]["retrieval_status"] == "answered"


@pytest.mark.asyncio
async def test_successful_question_survives_an_independent_failure(monkeypatch, followup):
    _, baseline, args = followup
    monkeypatch.setattr(memo, "_plan_trade_research", AsyncMock(return_value={"questions": [question(), question("Energy producer oil-price sensitivity?")]}))
    async def gather(self, runtime, **kwargs):
        if kwargs["question"].startswith("Energy"):
            raise RuntimeError("One provider task failed")
        return {"question_status": "answered", "results": [{"url": "https://example.org/treasury", "content": "Treasury evidence"}]}
    monkeypatch.setattr(ParallelSourceProvider, "gather", gather)
    evidence, runs, report = await memo._run_targeted_research(**args)
    assert len(runs) == 2 and len(evidence["facts"]) > len(baseline["facts"])
    assert len(report["unresolved"]) == 1 and report["status"] == "with_limitations"


@pytest.mark.asyncio
async def test_unsearchable_material_question_is_deferred_not_reported_as_unnecessary(monkeypatch, followup):
    _, baseline, args = followup
    monkeypatch.setattr(memo, "_plan_trade_research", AsyncMock(return_value={"questions": [question("x" * 351)]}))
    gather = AsyncMock(side_effect=AssertionError("Do not send oversized requests"))
    monkeypatch.setattr(ParallelSourceProvider, "gather", gather)
    evidence, _, report = await memo._run_targeted_research(**args)
    assert report["status"] == "deferred" and evidence["unresolved_market_questions"]
    assert evidence["facts"] == baseline["facts"]
    gather.assert_not_awaited()


def test_optional_research_error_is_warning_not_failed_memo():
    artifact = {"pipeline_status": "complete", "portfolio_snapshot": {"portfolio": {"cash_pct": 100}},
        "macro_positioning": {"asset_class_targets": [{"asset_class": "cash", "target_pct": 100, "min_pct": 100, "max_pct": 100}]},
        "structured_data": {}, "evidence_brief": {"evidence_status": "complete"},
        "stage_receipts": [{"stage": "trade_followup:parallel", "status": "failed", "optional": True, "error": "Network failure"}],
        "evidence_runs": [{"label": "trade_followup", "supplementary": True, "error": "Network failure"}]}
    health = analysis_health(artifact)
    assert health["status"] == "complete" and health["warnings"]
    assert health["label"] == "Analysis complete with limitations"


@pytest.mark.asyncio
async def test_initial_discovery_reuses_legacy_paid_tavily_evidence(monkeypatch, tmp_path):
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    token = CURRENT_RUNTIME.set(runtime)
    query = "Frozen research request"
    settings = {"query": f"{query}\nResearch cutoff: {runtime.started_at}. Exclude later information and distinguish historical observation dates from publication dates.",
        "mode": "deep", "max_sources": memo.DEFAULT_MAX_SOURCES_DEEP, "profile": "macro-v1"}
    retained = {"provider": "tavily", "results": [{"url": "https://example.org/retained", "content": "Paid evidence"}]}
    await runtime.research("tavily", settings, AsyncMock(return_value=retained))
    gather = AsyncMock(side_effect=AssertionError("Do not repay for initial discovery"))
    monkeypatch.setattr(ParallelSourceProvider, "gather", gather)
    try:
        discovery, _ = await memo._run_research_lanes(query, "deep")
    finally:
        CURRENT_RUNTIME.reset(token)
    assert discovery["provider"] == "tavily" and discovery["results"] == retained["results"]
    gather.assert_not_awaited()
