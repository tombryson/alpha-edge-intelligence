import asyncio
import json
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

import portfolio_positioning_memo as memo
from backend import model_routing
from backend.portfolio_retrieval import ParallelSourceProvider
from backend.portfolio_runtime import CURRENT_LANE, CURRENT_RUNTIME, PortfolioRuntime
from backend.research.providers.perplexity import PerplexityResearchProvider


@pytest.mark.asyncio
@pytest.mark.parametrize("processor", ["ultra2x", "ultra4x"])
async def test_initial_lanes_use_search_regardless_of_deep_processor_and_resume_without_new_calls(tmp_path, monkeypatch, processor):
    monkeypatch.setattr(model_routing, "_STORE_PATH", tmp_path / "routing.json")
    monkeypatch.setenv("PORTFOLIO_POSITIONING_MARKET_CONTEXT_PROCESSOR", processor)
    monkeypatch.setattr(memo, "DEFAULT_DEEP_EVIDENCE_RUNS", 3)
    posts = []

    def handler(request):
        assert request.method == "POST" and request.url.path == "/v1/search"
        body = json.loads(request.content)
        posts.append(body)
        assert body["mode"] == "advanced" and "processor" not in body
        assert body["search_queries"]
        return httpx.Response(200, json={"search_id": f"search_{len(posts)}", "results": [
            {"url": f"https://example.org/{len(posts)}", "excerpts": ["Original release text"]}]})

    monkeypatch.setattr(memo, "ParallelSourceProvider", lambda **kwargs: ParallelSourceProvider(
        api_key="test", transport=httpx.MockTransport(handler), poll_seconds=0, **kwargs))
    grok = AsyncMock(side_effect=AssertionError("Unexpected xAI call"))
    perplexity = Mock(side_effect=AssertionError("Portfolio research must not construct a Perplexity client"))
    monkeypatch.setattr(memo, "_fetch_xai_macro_environment_summary", grok)
    monkeypatch.setattr(PerplexityResearchProvider, "__init__", perplexity)
    checkpoint = tmp_path / "checkpoint.json"

    async def collect(runtime):
        token = CURRENT_RUNTIME.set(runtime)
        try:
            return await asyncio.gather(*(memo._run_single_evidence_lane(
                query=spec["query"], mode="deep", asset_class_vocabulary=[], lane_label=spec["label"],
                lane_focus=spec["focus"], include_coverage_checklist=spec["include_coverage_checklist"],
                search_queries=spec["search_queries"], structure=False)
                for spec in memo._build_evidence_lane_specs("Neutral research", "deep")))
        finally:
            CURRENT_RUNTIME.reset(token)

    runtime = PortfolioRuntime(checkpoint)
    lanes = await collect(runtime)
    assert len(posts) == len(lanes) == 3
    perplexity.assert_not_called()
    grok.assert_not_awaited()
    assert len(runtime.receipts) == 3
    assert next(row for row in runtime.progress.snapshot()["phases"] if row["id"] == "research")["total"] == 3
    assert all(lane["macro_news"] == {} and lane["parallel"]["model"] == "search:advanced" and "perplexity" not in lane for lane in lanes)
    assert all(lane["parallel"]["results"][0]["content"] == "Original release text" for lane in lanes)
    assert await collect(PortfolioRuntime(checkpoint, resume=checkpoint)) == lanes
    assert len(posts) == 3
    perplexity.assert_not_called()


@pytest.mark.asyncio
async def test_recovery_preserves_cached_grok_provenance_without_dispatch(tmp_path, monkeypatch):
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    token = CURRENT_RUNTIME.set(runtime)
    lane_token = CURRENT_LANE.set("macro_regime")
    query = f"Neutral research\nResearch cutoff: {runtime.started_at}. Exclude information published later."
    original = {"provider": "xai", "model": memo.DEFAULT_MACRO_NEWS_MODEL, "summary": "Previously paid Grok research"}
    try:
        await runtime.research("grok_research", {"query": query, "model": memo.DEFAULT_MACRO_NEWS_MODEL,
            "max_tokens": memo.LEGACY_MACRO_NEWS_MAX_TOKENS, "temperature": memo.DEFAULT_MACRO_NEWS_TEMPERATURE,
            "max_attempts": memo.DEFAULT_MACRO_NEWS_MAX_ATTEMPTS, "profile": "native-stream-v2"},
            AsyncMock(return_value=original))
        grok = AsyncMock(side_effect=AssertionError("Do not repeat Grok"))
        monkeypatch.setattr(memo, "_fetch_xai_macro_environment_summary", grok)
        monkeypatch.setattr(memo, "_run_research_lanes", AsyncMock(return_value=({"provider": "parallel"}, {})))
        lane = await memo._run_single_evidence_lane(query="Neutral research", mode="deep", asset_class_vocabulary=[],
            lane_label="macro_regime", lane_focus="Current rates?", include_coverage_checklist=False, structure=False)
        assert lane["macro_news"] == original
        assert runtime.receipts[-1]["reused"]
        grok.assert_not_awaited()
    finally:
        CURRENT_LANE.reset(lane_token)
        CURRENT_RUNTIME.reset(token)
