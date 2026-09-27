import json
from unittest.mock import AsyncMock

import httpx
import pytest

from backend import openrouter
from backend.portfolio_evidence import validate_stage
from backend.portfolio_recovery import parse_json_object
from backend.portfolio_runtime import PortfolioRuntime, workload_summary


def stream_response(status):
    events = [{"id": "failed-generation", "model": "resolved-model", "provider": "provider-name",
        "choices": [{"index": 0, "delta": {"content": '{"answer":'}, "finish_reason": None}]},
        {"choices": [{"index": 0, "finish_reason": "error", "error": {
            "code": status, "message": "Upstream idle timeout exceeded", "metadata": {"error_type": "timeout"}}}]}]
    return httpx.Response(200, headers={"content-type": "text/event-stream"},
        text="".join("data: " + json.dumps(event) + "\n\n" for event in events))


@pytest.mark.asyncio
@pytest.mark.parametrize("status,retryable", [(504, True), (503, True), (402, False), (400, False), (None, False)])
async def test_only_explicit_transient_terminal_errors_are_retryable(monkeypatch, status, retryable):
    client = httpx.AsyncClient
    transport = httpx.MockTransport(lambda _: stream_response(status))
    monkeypatch.setattr(openrouter.httpx, "AsyncClient", lambda **kwargs: client(transport=transport, **kwargs))
    result = await openrouter.query_model("requested-model", [], on_progress=AsyncMock(), include_error_details=True)
    assert result["error_retryable"] is retryable
    assert result["terminal_error"] and result["request_accepted"]
    assert result["outcome_uncertain"] is False
    assert result["content"] == '{"answer":' and result["id"] == "failed-generation"
    assert result["provider"] == "provider-name" and result["resolved_model"] == "resolved-model"
    assert json.loads(result["error_body"])["error"]["code"] == status


@pytest.mark.asyncio
async def test_runtime_retains_failed_paid_response_and_only_retries_its_stage(monkeypatch, tmp_path):
    client = httpx.AsyncClient
    calls = []
    def respond(request):
        calls.append(json.loads(request.content))
        if len(calls) == 1:
            return stream_response(504)
        return httpx.Response(200, json={"id": "completed-generation", "choices": [
            {"message": {"content": '{"answer":"saved"}'}, "finish_reason": "stop"}]})
    monkeypatch.setattr(openrouter.httpx, "AsyncClient", lambda **kwargs: client(transport=httpx.MockTransport(respond), **kwargs))
    runtime = PortfolioRuntime(tmp_path / "run.checkpoint.json")
    prompt = {"task": "Review", "required_schema": {"answer": "string"}}
    result = await runtime.query(openrouter.query_model, "model",
        [{"role": "user", "content": json.dumps(prompt)}], parser=parse_json_object, validator=validate_stage)
    assert result["stage_status"] == "complete" and len(calls) == 2
    assert [r["status"] for r in runtime.receipts] == ["failed", "complete"]
    assert runtime.receipts[0]["request_id"] == "failed-generation"
    assert runtime.receipts[0]["raw_response"]["content"] == '{"answer":'
    assert runtime.receipts[1]["request_id"] == "completed-generation"
    assert workload_summary(runtime.receipts)["retry_requests"] == 1
    assert calls[0]["messages"] == calls[1]["messages"]
    assert all("max_tokens" not in call for call in calls)


@pytest.mark.asyncio
async def test_repeated_terminal_failure_respects_existing_attempt_budget(monkeypatch):
    client = httpx.AsyncClient
    calls = []
    def respond(request):
        calls.append(request)
        return stream_response(504)
    monkeypatch.setattr(openrouter.httpx, "AsyncClient", lambda **kwargs: client(transport=httpx.MockTransport(respond), **kwargs))
    runtime = PortfolioRuntime()
    result = await runtime.query(openrouter.query_model, "model",
        [{"role": "user", "content": '{"task":"Review","required_schema":{"answer":"string"}}'}],
        parser=parse_json_object, validator=validate_stage)
    assert result["stage_status"] == "failed" and len(calls) == 3
    assert len(runtime.receipts) == 3


@pytest.mark.asyncio
async def test_header_request_identity_is_retained_before_first_token(monkeypatch):
    client = httpx.AsyncClient
    transport = httpx.MockTransport(lambda _: httpx.Response(200,
        headers={"content-type": "text/event-stream", "x-generation-id": "header-id"}, text=": heartbeat\n\n"))
    monkeypatch.setattr(openrouter.httpx, "AsyncClient", lambda **kwargs: client(transport=transport, **kwargs))
    progress = AsyncMock()
    result = await openrouter.query_model("model", [], on_progress=progress)
    assert result["id"] == "header-id" and result["outcome_uncertain"]
    assert result["error_retryable"] is False
    assert progress.call_args_list[0].args[0] == {"activity": "provider_connected", "id": "header-id"}


@pytest.mark.asyncio
@pytest.mark.parametrize("terminal", [True, False])
async def test_json_stream_fallback_keeps_content_identity_and_known_outcome(monkeypatch, terminal):
    client = httpx.AsyncClient
    choice = {"message": {"content": "partial", "reasoning_details": [{"text": "reason"}]}}
    if terminal:
        choice.update(finish_reason="error", error={"code": 504, "message": "timeout"})
    transport = httpx.MockTransport(lambda _: httpx.Response(200, headers={"x-generation-id": "header-id"},
        json={"provider": "provider", "model": "resolved", "usage": {"cost": 0}, "choices": [choice]}))
    monkeypatch.setattr(openrouter.httpx, "AsyncClient", lambda **kwargs: client(transport=transport, **kwargs))
    result = await openrouter.query_model("requested", [], on_progress=AsyncMock())
    assert result["id"] == "header-id" and result["content"] == "partial"
    assert result["provider"] == "provider" and result["usage"] == {"cost": 0}
    assert result["outcome_uncertain"] is not terminal
    assert result["error_retryable"] is terminal
    if terminal:
        assert result["resolved_model"] == "resolved" and result["terminal_error"]


@pytest.mark.asyncio
async def test_final_error_chunk_can_also_contain_content(monkeypatch):
    client = httpx.AsyncClient
    event = {"choices": [{"delta": {"content": "retained"}, "finish_reason": "error"}]}
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text="data: " + json.dumps(event) + "\n\n"))
    monkeypatch.setattr(openrouter.httpx, "AsyncClient", lambda **kwargs: client(transport=transport, **kwargs))
    result = await openrouter.query_model("model", [], on_progress=AsyncMock())
    assert result["content"] == "retained" and result["terminal_error"]
    assert result["error_retryable"] is False
