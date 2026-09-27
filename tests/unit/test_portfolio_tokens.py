import json
from unittest.mock import AsyncMock

import pytest

import portfolio_positioning_memo as memo
from backend import portfolio_funding as funding
from backend.portfolio_evidence import validate_stage
from backend.portfolio_runtime import CURRENT_LANE, CURRENT_RUNTIME, PortfolioRuntime, digest
from backend.portfolio_tokens import OUTPUT_LIMIT_KEYS, without_output_limit


@pytest.mark.parametrize("requested", [None, 0, 4000, 12000, 20000, 32000, 48000, 128000])
@pytest.mark.parametrize("parameter", sorted(OUTPUT_LIMIT_KEYS))
@pytest.mark.asyncio
async def test_runtime_never_forwards_an_application_output_limit(requested, parameter):
    settings = {parameter: requested, "reasoning_effort": "medium"}
    assert without_output_limit(settings) == {"reasoning_effort": "medium"}
    assert settings[parameter] == requested
    runtime = PortfolioRuntime()
    client = AsyncMock(return_value={"content": '{"answer":"complete"}'})
    result = await runtime.query(client, "test/model", [{"role": "user", "content": json.dumps({
        "task": "Extract facts", "required_schema": {"answer": "string"}})}],
        parser=memo._extract_json_object, validator=validate_stage, **settings)
    assert result["stage_status"] == "complete"
    assert not OUTPUT_LIMIT_KEYS.intersection(client.call_args.kwargs)
    assert not OUTPUT_LIMIT_KEYS.intersection(runtime.receipts[-1]["request_settings"])


@pytest.mark.parametrize("schema", [
    {"facts": []}, {"executive_summary": "string"}, {"fact_checks": []},
    {"asset_class_targets": [{"asset_class": "string"}]}, {"allocation_details": []},
    {"play_assessments": []}, {"target_updates": []}, {"portfolio_level_comments": []},
])
@pytest.mark.asyncio
async def test_every_stage_wrapper_omits_output_limits(schema):
    runtime = PortfolioRuntime()
    runtime.query = AsyncMock(return_value={"content": "{}", "stage_status": "complete"})
    token = CURRENT_RUNTIME.set(runtime)
    try:
        await memo._query_stage("test/model", [{"role": "user", "content": json.dumps({
            "task": "Portfolio stage", "required_schema": schema})}], max_tokens=12000)
    finally:
        CURRENT_RUNTIME.reset(token)
    assert not OUTPUT_LIMIT_KEYS.intersection(runtime.query.call_args.kwargs)


@pytest.mark.asyncio
async def test_credit_forecast_warns_without_capping_or_blocking_output(monkeypatch):
    snapshot = {"available_usd": 0.01, "prices": {"test/model": {"prompt": 0, "completion": 0.000001}},
                "models": {"test/model": {"top_provider": {"max_completion_tokens": 196608}}}}
    monkeypatch.setattr(funding, "funding_snapshot", AsyncMock(return_value=snapshot))
    client = AsyncMock(return_value={"content": "complete"})
    response = await funding.FundingGuard().call(client, "test/model", [], max_tokens=12000)
    assert response["funding_estimate"]["low_balance_warning"] is True
    assert response["funding_estimate"]["output_tokens_estimate"] != 196608
    snapshot["available_usd"] = 1
    await funding.FundingGuard().call(client, "test/model", [], max_tokens=12000)
    assert not OUTPUT_LIMIT_KEYS.intersection(client.call_args.kwargs)
    await funding.FundingGuard().call(client, "test/model", [], max_tokens=128000)
    assert not OUTPUT_LIMIT_KEYS.intersection(client.call_args.kwargs)


def test_credit_forecast_does_not_require_or_use_output_capacity():
    snapshot = {"prices": {"test/model": {"prompt": 0, "completion": 0.000001}}}
    estimate = funding.estimate_request(snapshot, "test/model", [])
    snapshot["models"] = {"test/model": {"context_length": 1000000}}
    assert funding.estimate_request(snapshot, "test/model", []) == estimate
    snapshot["models"]["test/model"]["top_provider"] = {"max_completion_tokens": 128000}
    assert funding.estimate_request(snapshot, "test/model", []) == estimate


@pytest.mark.asyncio
@pytest.mark.parametrize("cap", [32000, 64000, 128000])
@pytest.mark.parametrize("change", [None, "model", "prompt", "settings", "truncated", "failed"])
async def test_legacy_capped_checkpoint_reuses_only_identical_complete_work(tmp_path, cap, change):
    prompt = {"task": "Extract facts", "required_schema": {"answer": "string"}}
    stage = f"{CURRENT_LANE.get()}:Extract facts"
    code = {"portfolio_tokens.py": "legacy-capped-code"}
    settings = {"max_tokens": cap, "reasoning_effort": "medium"}
    key = digest({"stage": stage, "model": "test/model", "prompt": prompt, "settings": settings, "contract": 3, "code": code})
    response = {"content": '{"answer":"saved"}', "finish_reason": "length" if change == "truncated" else "stop"}
    receipt = {"stage": stage, "model": "test/model", "input_hash": key, "prompt": prompt,
        "request_settings": {**settings, "response_format": {"type": "json_object"}},
        "status": "failed" if change == "failed" else "complete", "finish_reason": response["finish_reason"]}
    checkpoint = tmp_path / "old.checkpoint.json"
    checkpoint.write_text(json.dumps({"code_manifest": code, "stage_receipts": [receipt],
        "stage_cache": {key: {"receipt": receipt, "result": response}}}))
    runtime = PortfolioRuntime(tmp_path / "new.checkpoint.json", checkpoint)
    client = AsyncMock(return_value={"content": '{"answer":"new"}', "finish_reason": "stop"})
    if change == "prompt":
        prompt["evidence"] = "changed evidence"
    result = await runtime.query(client, "changed/model" if change == "model" else "test/model",
        [{"role": "user", "content": json.dumps(prompt)}], parser=memo._extract_json_object, validator=validate_stage,
        reasoning_effort="low" if change == "settings" else "medium")
    assert json.loads(result["content"])["answer"] == ("saved" if change is None else "new")
    assert client.await_count == (0 if change is None else 1)
    if change is None:
        assert runtime.receipts[-1]["reused_from_input_hash"] == key
        # Historical receipts keep the actual old settings; only new requests are uncapped.
        assert runtime.receipts[-1]["request_settings"]["max_tokens"] == cap
        runtime.save()
        resumed = PortfolioRuntime(resume=runtime.checkpoint)
        await resumed.query(client, "test/model", [{"role": "user", "content": json.dumps(prompt)}],
            parser=memo._extract_json_object, validator=validate_stage, reasoning_effort="medium")
        client.assert_not_awaited()


@pytest.mark.asyncio
async def test_runtime_and_credit_guard_send_no_output_limit_on_openrouter_wire(monkeypatch):
    import httpx
    from backend import openrouter

    payloads = []
    def handle(request):
        payloads.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"answer":"complete"}'},
            "finish_reason": "stop"}], "usage": {"completion_tokens": 98304}})

    original = httpx.AsyncClient
    monkeypatch.setattr(openrouter.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs))
    monkeypatch.setattr(funding, "funding_snapshot", AsyncMock(return_value={"available_usd": 100,
        "prices": {"test/model": {"prompt": 0, "completion": 0.000001}},
        "models": {"test/model": {"top_provider": {"max_completion_tokens": 196608}}}}))
    runtime = PortfolioRuntime()
    runtime.funding_guard = funding.FundingGuard()
    result = await runtime.query(openrouter.query_model, "test/model",
        [{"role": "user", "content": json.dumps({"task": "Evidence extraction", "required_schema": {"answer": "string"}})}],
        parser=memo._extract_json_object, validator=validate_stage, max_tokens=32000)
    assert result["stage_status"] == "complete"
    assert len(payloads) == 1
    assert not OUTPUT_LIMIT_KEYS.intersection(payloads[0])
    assert runtime.receipts[-1]["usage"]["completion_tokens"] == 98304
