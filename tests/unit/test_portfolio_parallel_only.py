from unittest.mock import AsyncMock, Mock

import pytest

import portfolio_positioning_memo as memo
from backend.portfolio_runtime import CURRENT_LANE, CURRENT_RUNTIME, PortfolioRuntime
from backend.portfolio_evidence import research_packet
from backend.research.providers.perplexity import PerplexityResearchProvider


@pytest.mark.asyncio
@pytest.mark.parametrize("change", [None, "query", "lane", "cutoff", "failed"])
async def test_only_matching_completed_perplexity_evidence_is_retained_without_client(tmp_path, monkeypatch, change):
    checkpoint = tmp_path / "old.json"
    original_runtime = PortfolioRuntime(checkpoint)
    lane_token = CURRENT_LANE.set("macro_regime")
    query = "Frozen macro research"
    original = {"provider": "perplexity", "model": "original/model", "research_summary": "Previously paid research",
        "results": [{"url": "https://example.org/release", "title": "Original release", "content": "Original source text"}]}
    settings = {"query": f"{query}\nResearch cutoff: {original_runtime.started_at}. Exclude later information and distinguish historical observation dates from publication dates.",
        "mode": "deep", "max_sources": memo.DEFAULT_MAX_SOURCES_DEEP, "profile": "macro-v1", "model": "original/model"}
    try:
        await original_runtime.research("perplexity", settings, AsyncMock(return_value=(
            {"provider": "perplexity", "error": "Perplexity API error: 401", "results": []} if change == "failed" else original)), required=False)
        await original_runtime.asave()
        runtime = PortfolioRuntime(tmp_path / "new.json", resume=checkpoint)
        if change == "lane":
            CURRENT_LANE.set("sector_leadership")
        if change == "cutoff":
            runtime.started_at = "2000-01-01T00:00:00Z"
        token = CURRENT_RUNTIME.set(runtime)
        client = Mock(side_effect=AssertionError("No new Perplexity client, including recovery"))
        monkeypatch.setattr(PerplexityResearchProvider, "__init__", client)
        monkeypatch.setenv("PERPLEXITY_MODEL", "different/current-model")
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
        parallel = AsyncMock(return_value={"provider": "parallel", "research_summary": "New Parallel research"})
        monkeypatch.setattr(memo.ParallelSourceProvider, "gather", parallel)
        try:
            source, retained = await memo._run_research_lanes("Different question" if change == "query" else query, "deep")
        finally:
            CURRENT_RUNTIME.reset(token)
        assert source["provider"] == "parallel"
        parallel.assert_awaited_once()
        client.assert_not_called()
        if change is None:
            assert retained == original
            receipt = runtime.receipts[-1]
            assert receipt["reused"] and receipt["model"] == "original/model"
            packet = research_packet([{"perplexity": retained}], runtime.started_at)
            assert any(row["url"] == "https://example.org/release" for row in packet["sources"])
        else:
            assert retained == {}
            assert not any(row.get("reused") and row["stage"].endswith(":perplexity") for row in runtime.receipts)
    finally:
        CURRENT_LANE.reset(lane_token)


@pytest.mark.asyncio
async def test_parallel_failure_does_not_dispatch_a_perplexity_fallback(monkeypatch):
    runtime = PortfolioRuntime()
    token = CURRENT_RUNTIME.set(runtime)
    client = Mock(side_effect=AssertionError("No Perplexity fallback"))
    monkeypatch.setattr(PerplexityResearchProvider, "__init__", client)
    parallel = AsyncMock(side_effect=TimeoutError("Parallel unavailable"))
    monkeypatch.setattr(memo.ParallelSourceProvider, "gather", parallel)
    try:
        source, retained = await memo._run_research_lanes("Current rates?", "deep")
    finally:
        CURRENT_RUNTIME.reset(token)
    assert source["error"] == "Parallel unavailable" and source["results"] == []
    assert retained == {}
    client.assert_not_called()
    parallel.assert_awaited_once()
