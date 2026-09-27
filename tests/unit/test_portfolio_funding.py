import json
from copy import deepcopy
from unittest.mock import AsyncMock

import pytest

import portfolio_positioning_memo as memo
from backend import portfolio_funding as funding
from backend.portfolio_decisions import analysis_health
from backend.portfolio_evidence import validate_stage
from backend.portfolio_runtime import PortfolioRuntime, SUPPLEMENTARY_RESEARCH, workload_summary
from backend.portfolio_tokens import OUTPUT_LIMIT_KEYS


def snapshot(balance=6.29):
    return {"available_usd": balance,
        "prices": {"anthropic/claude-opus-5": {"prompt": 0.000005, "completion": 0.000025}},
        "models": {"anthropic/claude-opus-5": {"context_length": 1000000,
            "top_provider": {"max_completion_tokens": 128000}}}}


def receipt():
    return {"model": "anthropic/claude-opus-5", "stage": "decision_consistency:Check final claims",
        "input_hash": "saved-review", "status": "complete", "work_kind": "allocation",
        "payload_accounting": {"message_bytes": 716289},
        "usage": {"prompt_tokens": 294315, "completion_tokens": 36961, "cost": 2.3956}}


@pytest.mark.asyncio
async def test_september_21_review_is_affordable_without_byte_or_full_capacity_reservation(monkeypatch):
    monkeypatch.setattr(funding, "funding_snapshot", AsyncMock(return_value=snapshot()))
    client = AsyncMock(return_value={"content": "saved"})
    messages = [{"role": "user", "content": json.dumps({"task": "Check revised claims", "evidence": "x" * 700000})}]
    guard = funding.FundingGuard()
    response = await guard.call(client, "anthropic/claude-opus-5", messages,
        receipts=[receipt()], max_tokens=32000)
    estimate = response["funding_estimate"]
    assert 2 < estimate["estimated_request_usd"] < 3.1
    assert 280000 < estimate["input_tokens_estimate"] < 300000
    assert estimate["output_tokens_estimate"] == 36961
    assert estimate["low_balance_warning"] is False
    assert not OUTPUT_LIMIT_KEYS.intersection(client.call_args.kwargs)
    assert "receipts" not in client.call_args.kwargs
    assert guard.reserved == guard.reserved_minimum == 0


def test_estimate_deduplicates_reused_usage_and_ignores_other_models_and_failed_usage():
    row = receipt()
    others = [{**deepcopy(row), "input_hash": "other", "model": "other/model"},
        {**deepcopy(row), "input_hash": "failed", "status": "failed"}]
    result = funding.estimate_request(snapshot(), row["model"], [], receipts=[row, {**row, "reused": True}, *others])
    assert result["input_samples"] == result["output_samples"] == 1


@pytest.mark.asyncio
async def test_positive_balance_below_forecast_is_advisory_but_zero_balance_blocks(monkeypatch):
    state = snapshot(0.01)
    monkeypatch.setattr(funding, "funding_snapshot", AsyncMock(return_value=state))
    client = AsyncMock(return_value={"content": "retained"})
    response = await funding.FundingGuard().call(client, "anthropic/claude-opus-5", [])
    assert response["funding_estimate"]["low_balance_warning"]
    state["available_usd"] = 0
    with pytest.raises(funding.FundingRequired):
        await funding.FundingGuard().call(client, "anthropic/claude-opus-5", [])
    assert client.await_count == 1


@pytest.mark.asyncio
async def test_free_request_can_run_at_zero_credit(monkeypatch):
    monkeypatch.setattr(funding, "funding_snapshot", AsyncMock(return_value={
        "available_usd": 0, "prices": {"free/model": {"prompt": 0, "completion": 0}}}))
    client = AsyncMock(return_value={"content": "free"})
    assert (await funding.FundingGuard().call(client, "free/model", []))["content"] == "free"


@pytest.mark.asyncio
async def test_new_and_recovery_plans_are_advisory_with_positive_balance(monkeypatch):
    monkeypatch.setattr(funding, "funding_snapshot", AsyncMock(return_value=snapshot(0.01)))
    monkeypatch.setattr(funding, "estimate_plan", lambda *args: {("anthropic/claude-opus-5", "allocation"): 10})
    previous = {"stage_receipts": [receipt()]}
    assert (await funding.preflight({}, {}, previous))["status"] == "ready"
    report = await funding.preflight({}, {})
    assert report["status"] == "ready" and report["low_balance_warning"] and report["estimate_advisory"]
    assert report["unchecked_providers"] == ["Parallel"]
    assert report["top_up_usd"] > 0
    monkeypatch.setattr(funding, "funding_snapshot", AsyncMock(return_value=snapshot(0)))
    assert (await funding.preflight({}, {}))["status"] == "insufficient"


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["zero", "provider_402", "unverified"])
async def test_optional_funding_failure_keeps_memo_and_is_not_cached_as_success(monkeypatch, tmp_path, failure):
    mock = AsyncMock(return_value=snapshot(0 if failure == "zero" else 6.29))
    if failure == "unverified":
        mock.side_effect = ValueError("Credit service unavailable")
    monkeypatch.setattr(funding, "funding_snapshot", mock)
    runtime = PortfolioRuntime(tmp_path / "memo.checkpoint.json")
    runtime.partial["analyst_memo_markdown"] = "Saved investment analysis"
    runtime.funding_guard = funding.FundingGuard()
    client = AsyncMock(return_value={"error_status": 402, "error": "Insufficient provider credit"})
    prompt = {"task": "Check revised claims", "required_schema": {"answer": "string"}}
    token = SUPPLEMENTARY_RESEARCH.set(True)
    try:
        response = await runtime.query(client, "anthropic/claude-opus-5",
            [{"role": "user", "content": json.dumps(prompt)}],
            parser=memo._extract_json_object, validator=validate_stage)
    finally:
        SUPPLEMENTARY_RESEARCH.reset(token)
    assert response["stage_status"] == "failed" and response["warnings"]
    assert not runtime.cache
    assert runtime.receipts[-1]["optional"] is True
    assert "funding" not in runtime.partial
    assert runtime.partial["analyst_memo_markdown"] == "Saved investment analysis"
    assert workload_summary(runtime.receipts)["new_model_requests"] == (1 if failure == "provider_402" else 0)
    assert workload_summary(runtime.receipts)["new_research_requests"] == 0
    health = analysis_health({"stage_receipts": runtime.receipts})
    assert any(row["stage"] == runtime.receipts[-1]["stage"] for row in health["warnings"])
    saved = json.loads(runtime.checkpoint.read_text())
    assert saved["partial_artifact"]["analyst_memo_markdown"] == "Saved investment analysis"
    # A later required call still stops; optional failure does not waive real provider funding rules.
    with pytest.raises(funding.FundingRequired):
        await runtime.query(client, "anthropic/claude-opus-5",
            [{"role": "user", "content": json.dumps({**prompt, "task": "Required allocation"})}],
            parser=memo._extract_json_object, validator=validate_stage)
    assert client.await_count == (1 if failure == "provider_402" else 0)
