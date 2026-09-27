import asyncio
import json
import time
from unittest.mock import AsyncMock

import pytest

from backend import portfolio_funding as funding
from backend.openrouter import _build_error_response
from backend.portfolio_evidence import validate_stage
from backend.portfolio_recovery import parse_json_object
from backend.portfolio_runtime import PortfolioRuntime, workload_summary


def rejected(delay=0):
    return {"error_status": 402, "error_reason": "in_flight_budget_exhausted",
        "request_accepted": False, "retry_after_seconds": delay, "content": "",
        "error": "temporary provider reservation", "error_retryable": True}


@pytest.fixture
def funded(monkeypatch):
    snapshot = {"available_usd": 5.99, "prices": {"model": {"prompt": .000001, "completion": .000001}}}
    monkeypatch.setattr(funding, "funding_snapshot", AsyncMock(return_value=snapshot))
    return snapshot


def test_full_provider_reason_survives_display_body_truncation():
    body = json.dumps({"error": {"message": "x" * 1500, "code": 402,
        "metadata": {"reason": "in_flight_budget_exhausted", "headers": {"Retry-After": "120"}}}})
    result = _build_error_response(model="model", status=402, body=body,
        error_type="insufficient_credits", error_message="rejected", retryable=False, headers={})
    assert len(result["error_body"]) == 1000
    assert result["error_reason"] == "in_flight_budget_exhausted"
    assert result["retry_after_seconds"] == 120
    assert result["error_retryable"] and result["request_accepted"] is False


def test_malformed_retry_header_does_not_erase_known_rejection_reason():
    body = json.dumps({"error": {"metadata": {"reason": "in_flight_budget_exhausted"}}})
    result = _build_error_response(model="model", status=402, body=body, headers={"retry-after": "invalid"},
        error_type="http_error", error_message="rejected", retryable=False)
    assert result["request_accepted"] is False and result["error_type"] == "in_flight_budget"


def test_inband_provider_error_does_not_claim_the_request_was_unaccepted():
    result = _build_error_response(model="model", status=402,
        body=json.dumps({"error": {"metadata": {"reason": "in_flight_budget_exhausted"}}}),
        error_type="provider_error", error_message="stream error", retryable=False)
    assert result.get("request_accepted") is not False


@pytest.mark.asyncio
async def test_temporary_rejection_drains_existing_calls_without_poisoning_run(funded):
    guard = funding.FundingGuard()
    accepted, settle = asyncio.Event(), asyncio.Event()
    async def first(*args, **kwargs):
        accepted.set()
        await settle.wait()
        return {"content": "first paid output"}
    first_task = asyncio.create_task(guard.call(first, "model", []))
    await accepted.wait()
    response = await guard.call(AsyncMock(return_value=rejected()), "model", [])
    assert response["error_type"] == "in_flight_budget"
    assert guard.waiting is None
    client = AsyncMock(return_value={"content": "next output"})
    next_task = asyncio.create_task(guard.call(client, "model", []))
    await asyncio.sleep(.01)
    client.assert_not_awaited()
    settle.set()
    one, two = await asyncio.wait_for(asyncio.gather(first_task, next_task), timeout=1)
    assert one["content"] == "first paid output" and two["content"] == "next output"
    assert guard.inflight == 0 and guard.reserved == 0
    assert guard.inflight_limit == 1


@pytest.mark.asyncio
async def test_retry_after_is_honoured_even_with_no_local_requests(funded):
    guard = funding.FundingGuard()
    await guard.call(AsyncMock(return_value=rejected(.03)), "model", [])
    started = time.monotonic()
    await guard.call(AsyncMock(return_value={"content": "done"}), "model", [])
    assert time.monotonic() - started >= .02
    assert guard.waiting is None


@pytest.mark.asyncio
async def test_cancellation_releases_admission_and_reservations(funded):
    guard = funding.FundingGuard()
    guard.inflight_limit = 1
    started = asyncio.Event()
    async def blocked(*args, **kwargs):
        started.set()
        await asyncio.Event().wait()
    task = asyncio.create_task(guard.call(blocked, "model", []))
    await started.wait()
    waiting = asyncio.create_task(guard.call(AsyncMock(return_value={"content": "next"}), "model", []))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert (await asyncio.wait_for(waiting, 1))["content"] == "next"
    assert guard.inflight == guard.reserved == 0


@pytest.mark.asyncio
async def test_runtime_records_rejected_and_successful_attempt_separately(funded, tmp_path):
    runtime = PortfolioRuntime(tmp_path / "recovery.checkpoint.json")
    runtime.funding_guard = funding.FundingGuard()
    client = AsyncMock(side_effect=[rejected(), {"content": '{"answer":"retained"}', "id": "accepted-generation"}])
    response = await runtime.query(client, "model",
        [{"role": "user", "content": json.dumps({"task": "Finish memo", "required_schema": {"answer": "string"}})}],
        parser=parse_json_object, validator=validate_stage)
    assert response["stage_status"] == "complete"
    assert client.await_count == 2
    assert [r["status"] for r in runtime.receipts] == ["failed", "complete"]
    assert runtime.receipts[0]["failure_type"] == "in_flight_budget"
    assert workload_summary(runtime.receipts)["retry_requests"] == 1
    assert "funding" not in runtime.partial


@pytest.mark.asyncio
@pytest.mark.parametrize("extra", [{"request_accepted": True}, {"id": "already-accepted"}, {"outcome_uncertain": True}])
async def test_uncertain_or_accepted_request_is_not_treated_as_safe_to_resubmit(funded, extra):
    guard = funding.FundingGuard()
    with pytest.raises(funding.FundingRequired):
        await guard.call(AsyncMock(return_value={**rejected(), **extra}), "model", [])
    assert guard.inflight == 0
