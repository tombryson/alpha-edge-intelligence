import asyncio
import json
from copy import deepcopy
from unittest.mock import AsyncMock

import httpx
import pytest

import portfolio_positioning_memo as memo
from backend.portfolio_research import planning_prompt, pending_source_attempt
from backend.portfolio_retrieval import ParallelSourceProvider, ResearchBudget
from backend.portfolio_runtime import CURRENT_RUNTIME, PortfolioRuntime
from backend.portfolio_sources import hydrate_citations


def packet():
    return {"search_id": "search_test", "session_id": "session_test", "results": [
        {"url": "https://example.org/report", "title": "Primary report", "publish_date": "2026-09-01",
         "excerpts": ["Production declined by 10%."]}]}


def question(**updates):
    return {"question": "What are current production losses?", "topic": "oil", "economic_question": "output_loss",
        "geography": "global", "period": "September 2026", "horizon": "5 years",
        "required_dimensions": ["production"], "status": "unanswered", "material_reason": "Changes the scarcity premise",
        "reuse_assessment": "Existing prices do not establish flows", "asset_classes": ["oil_producers"],
        "decision_impact": "high", "critical_premise": True,
        "search_queries": ["oil production measured losses", "oil export terminal throughput"], **updates}


def evidence():
    return {"facts": [{"id": "flow", "metric": "production loss", "value": 10, "unit": "%", "source_ids": ["source"]}],
        "source_packet": {"sources": [{"id": "source", "url": "https://example.org/report", "excerpt": "Production declined by 10%."}]}}


@pytest.mark.asyncio
async def test_search_is_default_and_resumes_without_changing_model_or_duplicate_posts(tmp_path):
    calls = []
    async def handler(request):
        calls.append(request)
        body = json.loads(request.content)
        assert request.url.path == "/v1/search"
        assert body["mode"] == "advanced" and body["advanced_settings"]["max_results"] == 5
        assert body["client_model"] == "openai/gpt-6-luna-pro"
        assert body["search_queries"] == question()["search_queries"]
        assert "Research cutoff" in body["objective"]
        assert "processor" not in body and "task_spec" not in body
        await asyncio.sleep(0)
        result = packet()
        result["session_id"] = body["session_id"]
        result["results"].append({"url": "https://example.org/report?utm_source=test", "excerpts": ["Export losses persist."]})
        return httpx.Response(200, json=result)
    provider = ParallelSourceProvider(api_key="test", transport=httpx.MockTransport(handler))
    path = tmp_path / "search.json"
    runtime = PortfolioRuntime(path, record_store=True)
    kwargs = {"question": question()["question"], "search_queries": question()["search_queries"], "client_model": "openai/gpt-6-luna-pro"}
    results = await asyncio.gather(*(provider.gather(runtime, **kwargs) for _ in range(2)))
    assert results[0] == results[1] and len(calls) == 1
    assert len(results[0]["results"]) == 1 and "Export losses" in results[0]["results"][0]["content"]
    assert ResearchBudget(runtime).publish()["reserved_estimate_usd"] == .005
    resumed = PortfolioRuntime(path, resume=path, record_store=True)
    result = await provider.gather(resumed, **{**kwargs, "client_model": "anthropic/claude-opus-5.5"})
    assert result == results[0] and len(calls) == 1


@pytest.mark.asyncio
async def test_searches_for_independent_questions_run_concurrently(tmp_path):
    started, ready = [], asyncio.Event()
    async def handler(request):
        started.append(request)
        if len(started) == 2:
            ready.set()
        await asyncio.wait_for(ready.wait(), 1)
        return httpx.Response(200, json=packet())
    provider = ParallelSourceProvider(api_key="test", transport=httpx.MockTransport(handler))
    runtime = PortfolioRuntime(tmp_path / "concurrent.json")
    results = await asyncio.gather(*(provider.gather(runtime, question=q) for q in ("oil production losses", "gold mining margins")))
    assert all(row.get("results") for row in results) and len(runtime.cache) == 2


@pytest.mark.asyncio
async def test_search_receives_scope_and_gaps_not_the_full_observation_ledger(tmp_path):
    calls = []
    def handler(request):
        body = json.loads(request.content)
        calls.append(body)
        assert "measured exports" in body["objective"]
        assert "Middle East" in body["objective"]
        assert "known_observations" not in body["objective"]
        assert len(body["objective"]) < 5000
        return httpx.Response(200, json=packet())
    provider = ParallelSourceProvider(api_key="test", transport=httpx.MockTransport(handler))
    runtime = PortfolioRuntime(tmp_path / "focused.json")
    context = {"geography": "Middle East", "required_dimensions": ["measured exports"],
        "known_observations": [{"metric": "Production", "measurement": "Previously researched. " * 1000}]}
    result = await provider.gather(runtime, question="What are measured exports?", context=context)
    assert result["results"] and len(calls) == 1
    # New observations alone do not purchase the same unchanged question a second time.
    context["known_observations"].append({"metric": "Inventory", "value": 100})
    assert await provider.gather(runtime, question="What are measured exports?", context=context) == result
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_uncertain_search_is_not_repeated_after_model_change(tmp_path):
    calls = []
    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("Lost response", request=request)
    provider = ParallelSourceProvider(api_key="test", transport=httpx.MockTransport(handler))
    path = tmp_path / "uncertain.json"
    await provider.gather(PortfolioRuntime(path), question="measured production losses", client_model="old")
    result = await provider.gather(PortfolioRuntime(path, resume=path), question="measured production losses", client_model="new")
    assert "uncertain" in result["error"] and len(calls) == 1


@pytest.mark.asyncio
async def test_search_funding_failure_prevents_additional_paid_searches(tmp_path):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(402, json={"error": {"message": "Insufficient credit"}})
    provider = ParallelSourceProvider(api_key="test", transport=httpx.MockTransport(handler))
    runtime = PortfolioRuntime(tmp_path / "funding.json")
    first = await provider.gather(runtime, question="oil flows")
    second = await provider.gather(runtime, question="gold margins")
    assert first["http_status"] == second["http_status"] == 402 and len(calls) == 1
    assert ResearchBudget(runtime).publish()["reserved_estimate_usd"] == 0


@pytest.mark.asyncio
async def test_hydration_passes_exact_research_context_and_skips_complete_excerpts(tmp_path, monkeypatch):
    context = {"objective": "Establish measured exports, not restored capacity", "search_queries": ["oil export measured flows"],
        "session_id": "shared-question", "client_model": "openai/gpt-6-luna-pro"}
    extract = AsyncMock(return_value={"results": [{"url": "https://example.org/missing", "content": "Original export table"}]})
    monkeypatch.setattr("backend.portfolio_sources.extract_sources", extract)
    lanes = [{"parallel": {"retrieval_context": context, "results": [
        {"url": "https://example.org/report", "content": "Enough source text"},
        {"url": "https://example.org/missing", "content": ""}]}}]
    await hydrate_citations(lanes, PortfolioRuntime(tmp_path / "hydrate.json"))
    assert extract.await_count == 1
    assert extract.call_args.args[0] == ["https://example.org/missing"]
    assert extract.call_args.kwargs == context


def test_research_direction_uses_existing_decision_model_not_evidence_model(monkeypatch):
    monkeypatch.setattr(memo, "DEFAULT_DEEP_CHAIRMAN_MODEL", "anthropic/claude-opus-5.5")
    monkeypatch.setattr(memo, "DEFAULT_DEEP_SUMMARY_MODEL", "openai/gpt-6-luna-pro")
    assert memo._research_model_for_mode("deep") == "anthropic/claude-opus-5.5"
    assert memo._summary_model_for_mode("deep") == "openai/gpt-6-luna-pro"
    prompt = planning_prompt("independent", evidence(), {"research_cutoff": "2026-09-23"})
    schema = prompt["required_schema"]["questions"][0]
    assert "search_queries" in schema and "deep_research_reason" in schema
    assert "current_portfolio" not in prompt and "investment_plays" not in prompt
    assert all(spec["search_queries"] for spec in memo._build_evidence_lane_specs("neutral", "deep"))


@pytest.mark.asyncio
@pytest.mark.parametrize("answered,reason,impact,error,expected", [
    (True, "Resolve conflicting physical flow estimates", "high", False, 1),
    (False, "", "high", False, 1),
    (False, "Resolve conflicting physical flow estimates", "low", False, 1),
    (False, "Resolve conflicting physical flow estimates", "high", True, 1),
    (False, "Resolve conflicting physical flow estimates", "high", False, 2),
])
async def test_deep_research_only_for_successfully_processed_material_unresolved_questions(
        tmp_path, monkeypatch, answered, reason, impact, error, expected):
    calls = []
    async def gather(self, runtime, **kwargs):
        calls.append(kwargs)
        if error:
            return {"error": "Provider unavailable", "results": []}
        return {"results": packet()["results"], "provider_metadata": {"endpoint": "/v1/search"}}
    async def structure(lane, **kwargs):
        lane["evidence_brief"] = evidence()
        if answered:
            lane["evidence_brief"]["question_answers"] = [
                {"dimension": "production", "status": "answered", "answer": "Measured production declined", "fact_ids": ["flow"]}]
        return lane
    monkeypatch.setattr(memo.ParallelSourceProvider, "gather", gather)
    monkeypatch.setattr(memo, "_structure_evidence_lane", structure)
    runtime = PortfolioRuntime(tmp_path / "research.json")
    token = CURRENT_RUNTIME.set(runtime)
    try:
        result, lanes, _ = await memo._run_question_research(evidence(), "deep", {"phase": "independent", "questions": [
            question(deep_research_reason=reason, decision_impact=impact, critical_premise=impact == "high")]})
    finally:
        CURRENT_RUNTIME.reset(token)
    assert len(calls) == expected and result["facts"]
    assert not calls[0]["deep_research"]
    if expected == 2:
        assert calls[1]["deep_research"] and calls[1]["session_id"] == calls[0]["session_id"]
        assert lanes[1]["retrieval_options"]["deep_research"]


@pytest.mark.asyncio
async def test_inspect_selected_source_before_escalation_and_retain_other_evidence(tmp_path, monkeypatch):
    gather = AsyncMock(return_value={"results": [{"url": "https://example.org/report", "content": "Short excerpt"}],
        "retrieval_context": {"objective": "Measured production", "session_id": "same"}})
    extract = AsyncMock(return_value={"results": [{"url": "https://example.org/report", "content": "Full relevant table"}]})
    async def structure(lane, **kwargs):
        lane["evidence_brief"] = evidence()
        if "citation_inspection" in lane["label"]:
            lane["evidence_brief"]["question_answers"] = [{"dimension": "production", "status": "answered", "answer": "Source establishes measured losses", "fact_ids": ["flow"]}]
        else:
            lane["evidence_brief"]["source_urls_to_inspect"] = ["https://example.org/report", "https://unrequested.example/report"]
        return lane
    monkeypatch.setattr(memo.ParallelSourceProvider, "gather", gather)
    monkeypatch.setattr(memo, "_structure_evidence_lane", structure)
    monkeypatch.setattr("backend.portfolio_sources.extract_sources", extract)
    runtime = PortfolioRuntime(tmp_path / "inspection.json")
    token = CURRENT_RUNTIME.set(runtime)
    try:
        result, lanes, report = await memo._run_question_research(evidence(), "deep", {"phase": "independent", "questions": [question(deep_research_reason="Difficult reconciliation")]})
    finally:
        CURRENT_RUNTIME.reset(token)
    assert gather.await_count == 1 and extract.await_count == 1
    assert extract.call_args.args[0] == ["https://example.org/report"]
    assert report["answered"] == 1 and result["facts"]
    assert lanes[0]["citation_extraction"]["results"]


def test_pending_resume_keeps_exact_search_options():
    original = {**question(), "id": "q", "missing_dimensions": ["production"], "processing_status": "pending"}
    options = {"deep_research": True, "session_id": "paid-session", "client_model": "original", "search_queries": ["old exact query"]}
    saved = {"targeted_research_results": {"independent:q": {"phase": "independent", "query": original["question"],
        "question": deepcopy(original), "retrieval_context": {"required_dimensions": ["production"]},
        "retrieval_options": options, "parallel": {"resumable": True}}}}
    result = pending_source_attempt(original, saved, "independent")
    assert result["retrieval_options"] == options


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [
    {"results": [], "error": "Extraction outcome uncertain", "resumable": True},
    {"results": [], "failed_results": [{"url": "https://example.org/report", "error": "Page unavailable"}]},
    {"results": [], "provider_metadata": {"errors": ["Provider extraction failed"]}},
])
async def test_failed_selective_extraction_does_not_purchase_deep_research(tmp_path, monkeypatch, failure):
    gather = AsyncMock(return_value={"results": [{"url": "https://example.org/report", "content": "Partial source"}],
        "provider_metadata": {"endpoint": "/v1/search"}, "retrieval_context": {"objective": "Measured flows"}})
    extract = AsyncMock(return_value=failure)
    async def structure(lane, **kwargs):
        lane["evidence_brief"] = {**evidence(), "source_urls_to_inspect": ["https://example.org/report"]}
        return lane
    monkeypatch.setattr(memo.ParallelSourceProvider, "gather", gather)
    monkeypatch.setattr(memo, "_structure_evidence_lane", structure)
    monkeypatch.setattr("backend.portfolio_sources.extract_sources", extract)
    runtime = PortfolioRuntime(tmp_path / "failed-inspection.json")
    token = CURRENT_RUNTIME.set(runtime)
    try:
        result, _, report = await memo._run_question_research(evidence(), "deep", {"phase": "plays", "questions": [
            question(deep_research_reason="Reconcile conflicting physical flow reports")]})
    finally:
        CURRENT_RUNTIME.reset(token)
    assert gather.await_count == extract.await_count == 1
    assert result["facts"] and report["questions"][0]["inspection_status"] == "failed"


@pytest.mark.asyncio
async def test_ordinary_followup_uses_new_queries_same_session_and_no_task(tmp_path, monkeypatch):
    calls = []
    async def gather(self, runtime, **kwargs):
        calls.append(kwargs)
        if len(calls) == 2:
            return {"results": [], "error": "Supplementary search unavailable"}
        return {"results": [{"url": "https://example.org/report", "content": "Partial source"}],
            "provider_metadata": {"endpoint": "/v1/search"}}
    async def structure(lane, **kwargs):
        lane["evidence_brief"] = {**evidence(), "followup_question": "How much production is still shut in?",
            "followup_search_queries": ["oil shut in production volumes"]}
        return lane
    monkeypatch.setattr(memo.ParallelSourceProvider, "gather", gather)
    monkeypatch.setattr(memo, "_structure_evidence_lane", structure)
    runtime = PortfolioRuntime(tmp_path / "expansion.json")
    token = CURRENT_RUNTIME.set(runtime)
    try:
        result, lanes, _ = await memo._run_question_research(evidence(), "deep", {"phase": "independent", "questions": [question()]})
    finally:
        CURRENT_RUNTIME.reset(token)
    assert len(calls) == len(lanes) == 2
    assert not any(call["deep_research"] for call in calls)
    assert calls[1]["search_queries"] == ["oil shut in production volumes"]
    assert calls[1]["session_id"] == calls[0]["session_id"]
    assert calls[1]["exclude_urls"] == ["https://example.org/report"]
    assert result["facts"]


def test_deep_packet_preserves_additional_necessary_sources():
    from backend.portfolio_retrieval import normalize_result
    data = {"output": {"content": {"sources": []}, "basis": [{"citations": [
        {"url": f"https://example.org/{index}", "excerpts": [f"Distinct source {index}"]} for index in range(8)]}]}}
    assert len(normalize_result(data, limit=None)["results"]) == 8
    assert len(normalize_result(data)["results"]) == 5  # Historical receipt behaviour.


@pytest.mark.asyncio
async def test_expansion_budget_follows_priority_not_search_completion_order(tmp_path, monkeypatch):
    monkeypatch.setenv("PORTFOLIO_RESEARCH_BUDGET_USD", "0.015")
    calls, completed = [], []
    fast_done = asyncio.Event()
    async def gather(self, runtime, **kwargs):
        subject = kwargs["question"]
        calls.append(subject)
        if subject == "Important margins?":
            await asyncio.wait_for(fast_done.wait(), 2)
        elif subject == "Latest quote?":
            fast_done.set()
        completed.append(subject)
        return {"results": [{"url": "https://example.org/report", "content": "Source"}],
            "provider_metadata": {"endpoint": "/v1/search"}}
    async def structure(lane, **kwargs):
        lane["evidence_brief"] = {**evidence(), "followup_question": lane["question"]["question"] + " Remaining gap?"}
        return lane
    monkeypatch.setattr(memo.ParallelSourceProvider, "gather", gather)
    monkeypatch.setattr(memo, "_structure_evidence_lane", structure)
    runtime = PortfolioRuntime(tmp_path / "priority.json")
    token = CURRENT_RUNTIME.set(runtime)
    try:
        await memo._run_question_research(evidence(), "deep", {"phase": "independent", "questions": [
            question(question="Latest quote?", economic_question="quote", decision_dependency="market_quote"),
            question(question="Important margins?", economic_question="margins", decision_dependency="earnings",
                     decision_consequence="Whether producers earn sufficient returns")]})
    finally:
        CURRENT_RUNTIME.reset(token)
    assert completed[0] == "Latest quote?"
    assert calls == ["Important margins?", "Latest quote?", "Important margins? Remaining gap?"]
