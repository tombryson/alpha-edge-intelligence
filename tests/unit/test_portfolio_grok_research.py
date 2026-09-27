import argparse
import asyncio
import json
from unittest.mock import AsyncMock

import httpx
import pytest

import portfolio_positioning_memo as memo
from backend.portfolio_runtime import CURRENT_LANE, CURRENT_RUNTIME, PortfolioRuntime
from backend.research.providers import xai


def completed():
    return {"id": "research-1", "status": "completed", "usage": {"output_tokens": 2100}, "output": [
        {"type": "reasoning", "content": [{"type": "reasoning_text", "text": "Private reasoning"}]},
        {"type": "web_search_call", "action": {"sources": [{"url": "https://example.org/uncited-search-result"}]}}, {"type": "x_search_call"},
        {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Sourced research",
          "annotations": [{"type": "url_citation", "url": "https://example.org/data", "title": "Data"}]}]},
    ]}


def stream_response(*events):
    text = "".join(f"data: {json.dumps(event)}\n\n" for event in events)
    return httpx.Response(200, text=text, headers={"content-type": "text/event-stream"})


@pytest.fixture
def install_transport(monkeypatch):
    original = httpx.AsyncClient
    monkeypatch.setattr(xai.asyncio, "sleep", AsyncMock())

    def install(handler):
        transport = httpx.MockTransport(handler)
        monkeypatch.setattr(xai.httpx, "AsyncClient", lambda **kw: original(transport=transport, **kw))
    return install


async def fetch(**kwargs):
    return await xai.fetch_xai_research(api_key="test-only", api_url="https://api.x.ai/v1/responses",
                                       model="x-ai/grok-4.6", prompt="Original frozen prompt", **kwargs)


@pytest.mark.asyncio
async def test_streamed_research_uses_native_model_tools_and_research_budgets(install_transport):
    requests = []
    def handler(request):
        requests.append(request)
        return stream_response(
            {"type": "response.created", "response": {"id": "research-1", "status": "in_progress"}},
            {"type": "response.output_text.delta", "delta": "Sourced research"},
            {"type": "response.completed", "response": completed()},
        )
    install_transport(handler)
    updates = []
    result = await fetch(on_progress=updates.append)
    request = requests[0]
    payload = json.loads(request.content)
    assert payload["model"] == "grok-4.6"
    assert payload["stream"] is True
    assert "max_output_tokens" not in payload
    assert payload["tools"] == [{"type": "web_search"}, {"type": "x_search"}]
    assert request.extensions["timeout"]["read"] == 180
    assert result["success"] is True
    assert result["summary"] == "Sourced research"
    assert result["request_id"] == "research-1"
    assert result["tool_calls_count"] == 2
    assert result["usage"] == {"output_tokens": 2100}
    assert result["results"][0]["verification"] == "provider_citation_only"
    assert result["results"][0]["content"] == ""
    assert len(result["results"]) == 1
    assert updates[-1]["last_event"] == "response.completed"
    assert "test-only" not in json.dumps(result)


@pytest.mark.asyncio
async def test_empty_message_read_timeout_is_named_and_retried(install_transport):
    calls = []
    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ReadTimeout("")
        return httpx.Response(200, json=completed())
    install_transport(handler)
    result = await fetch()
    assert result["success"] is True
    assert result["request_count"] == 2
    assert result["attempts"][0]["error_type"] == "timeout"
    assert result["attempts"][0]["error"].startswith("ReadTimeout:")
    assert json.loads(calls[0].content) == json.loads(calls[1].content)


@pytest.mark.asyncio
@pytest.mark.parametrize("initial", [12000, 64000, 96000])
async def test_provider_truncation_is_retained_without_restoring_application_cap(install_transport, initial):
    budgets = []
    def handler(request):
        budgets.append(json.loads(request.content).get("max_output_tokens"))
        data = completed()
        if len(budgets) == 1:
            data.update(status="incomplete", incomplete_details={"reason": "max_output_tokens"})
        return stream_response({"type": "response.completed", "response": data})
    install_transport(handler)
    result = await fetch(max_tokens=initial)
    assert result["success"] is True
    assert budgets == [None, None]
    assert result["attempts"][0]["error_type"] == "output_truncated"
    assert result["attempts"][0]["raw_response"]["status"] == "incomplete"


@pytest.mark.asyncio
async def test_stream_disconnect_keeps_partial_evidence_without_accepting_it(install_transport):
    install_transport(lambda _: stream_response(
        {"type": "response.created", "response": {"id": "partial-1", "status": "in_progress"}},
        {"type": "response.output_text.delta", "delta": "Not finished"},
    ))
    result = await fetch()
    assert result["success"] is False
    assert result["summary"] == ""
    assert result["request_count"] == 2
    assert result["error_type"] == "transport_error"
    assert result["request_id"] == "partial-1"
    assert result["attempts"][0]["partial_text"] == "Not finished"


@pytest.mark.asyncio
async def test_absolute_deadline_also_stops_a_live_stream(install_transport):
    class HangingStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'data: {"type":"response.created","response":{"id":"slow"}}\n\n'
            await asyncio.Event().wait()
    install_transport(lambda _: httpx.Response(200, stream=HangingStream(), headers={"content-type": "text/event-stream"}))
    result = await fetch(timeout_seconds=0.01, max_attempts=1)
    assert result["success"] is False
    assert result["error_type"] == "timeout"
    assert result["request_id"] == "slow"
    assert "attempt limit 0.01s" in result["error"]


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [400, 401, 402, 403, 404])
async def test_permanent_http_rejections_do_not_retry(install_transport, status):
    install_transport(lambda _: httpx.Response(status, json={"error": "rejected"}))
    result = await fetch()
    assert result["success"] is False
    assert result["request_count"] == 1
    assert result["http_status"] == status
    assert f"HTTP {status}" in result["error"]


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [[], None, {"status": "completed", "output": []}, {"status": "failed", "error": "Provider failed"},
                                    {"status": "incomplete", "incomplete_details": "invalid"}])
async def test_invalid_empty_and_failed_responses_have_explicit_errors(install_transport, payload):
    install_transport(lambda _: httpx.Response(200, content=json.dumps(payload), headers={"content-type": "application/json"}))
    result = await fetch()
    assert result["success"] is False
    assert result["error"]
    assert result["error_type"]
    assert result["request_count"] == 1


@pytest.mark.asyncio
async def test_missing_credentials_do_not_make_request(install_transport):
    def unexpected(_):
        pytest.fail("Missing key must not send a request")
    install_transport(unexpected)
    result = await xai.fetch_xai_research(api_key="", api_url="https://api.x.ai/v1/responses", model="grok-4.6", prompt="test")
    assert result["attempted"] is False
    assert result["error_type"] == "authentication"


@pytest.mark.asyncio
async def test_research_receipts_never_lose_empty_exception_messages():
    runtime = PortfolioRuntime()
    result = await runtime.research("grok_research", {"model": "grok-4.6"}, AsyncMock(side_effect=httpx.ReadTimeout("")))
    assert result["error"].startswith("ReadTimeout:")
    assert runtime.receipts[0]["error"] == result["error"]
    assert runtime.receipts[0]["status"] == "failed"
    assert not runtime.cache


@pytest.mark.asyncio
async def test_failed_partial_research_is_not_cached_and_receipts_are_compact():
    runtime = PortfolioRuntime()
    result = {"success": False, "summary": "unfinished", "error": "", "attempts": [
        {"error_type": "timeout", "raw_response": {"id": "r1"}, "partial_text": "unfinished"}]}
    saved = await runtime.research("grok_research", {}, AsyncMock(return_value=result))
    assert saved["error"]
    assert not runtime.cache
    assert "partial_text" not in runtime.receipts[0]["attempts"][0]
    retained = next(iter(runtime.partial["retained_research"].values()))["result"]
    assert retained["attempts"][0]["partial_text"] == "unfinished"


@pytest.mark.asyncio
async def test_pipeline_wrapper_logs_live_progress_and_checkpoints_terminal_research(tmp_path, monkeypatch, capsys):
    captured = {}
    async def provider(**kwargs):
        captured.update(kwargs)
        kwargs["on_progress"]({"attempt": 1, "last_event": "response.created", "elapsed_seconds": 0.5,
                               "response_id": "live-id", "event_count": 1, "tool_calls_count": 0})
        assert not runtime.checkpoint.exists()
        return {"success": True, "summary": "Complete research"}
    monkeypatch.setattr(memo, "fetch_xai_research", provider)
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    token = CURRENT_RUNTIME.set(runtime)
    lane_token = CURRENT_LANE.set("macro_regime")
    try:
        result = await runtime.research("grok_research", {"query": "Frozen query"},
            lambda: memo._fetch_xai_macro_environment_summary(user_query="Frozen query"))
        assert result["success"] is True
    finally:
        CURRENT_LANE.reset(lane_token)
        CURRENT_RUNTIME.reset(token)
    saved = json.loads(runtime.checkpoint.read_text())
    assert saved["partial_artifact"]["research_progress"]["macro_regime:grok_research"]["response_id"] == "live-id"
    assert "response_id=live-id" in capsys.readouterr().out
    assert captured["timeout_seconds"] == memo.DEFAULT_MACRO_NEWS_TIMEOUT_SECONDS
    assert "max_tokens" not in captured
    assert captured["prompt"] == memo._build_macro_environment_news_prompt(user_query="Frozen query")


@pytest.mark.asyncio
async def test_failed_provider_does_not_stop_other_usable_research(tmp_path, monkeypatch):
    good = {"success": True, "research_summary": "Retained source material", "results": [{"url": "https://example.org", "content": "Source text"}]}
    grok = AsyncMock(side_effect=AssertionError("Fresh portfolio research must not call Grok"))
    monkeypatch.setattr(memo, "_fetch_xai_macro_environment_summary", grok)
    monkeypatch.setattr(memo.ParallelSourceProvider, "gather", AsyncMock(side_effect=[
        {"success": False, "error": "ReadTimeout: timed out", "error_type": "timeout"}, good, good]))
    monkeypatch.setattr(memo, "DEFAULT_DEEP_EVIDENCE_RUNS", 3)
    structured = AsyncMock(return_value={"evidence_status": "complete", "facts": [{"id": "retained"}]})
    monkeypatch.setattr(memo, "_build_evidence_brief", structured)
    reconcile = AsyncMock(return_value={"evidence_status": "complete", "facts": [{"id": "retained"}]})
    monkeypatch.setattr(memo, "_run_evidence_reconciliation", reconcile)
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    token = CURRENT_RUNTIME.set(runtime)
    try:
        brief, lanes, citations = await memo._run_evidence_ensemble(query="test", mode="deep", asset_class_vocabulary=[])
    finally:
        CURRENT_RUNTIME.reset(token)
    assert structured.await_count == 2
    grok.assert_not_awaited()
    assert brief["evidence_status"] == "complete" and citations
    assert len(lanes) == 3
    assert all(lane["parallel"]["research_summary"] == "Retained source material" for lane in lanes[1:])
    assert "ReadTimeout" in lanes[0]["evidence_brief"]["stage_error"]
    assert all("perplexity" not in lane for lane in lanes)


@pytest.mark.parametrize("lane", [{}, {"macro_news": {"error": ""}}, {"error": "Provider exception"}])
def test_missing_research_cannot_pass_barrier(lane):
    assert memo._research_failure(lane)
