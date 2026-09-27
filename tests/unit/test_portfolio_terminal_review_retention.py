from copy import deepcopy
import json
from unittest.mock import AsyncMock

import pytest

from backend import portfolio_independent as independent
from backend.portfolio_recovery import parse_json_object, retain_terminal_review
from backend.portfolio_requests import review_findings
from backend.portfolio_runtime import PortfolioRuntime, workload_summary


def review_fixture():
    prompt = independent.review_prompt("defensive_regime_reviewer", {"facts": []},
        {"research_cutoff": "2026-09-22"}, {}, {}, {}, [])
    prompt["review_scope"] = {"case_ids": ["oil", "gold"]}
    finding = {"asset_class": "oil", "kind": "research_gap", "argument": "Producer margins remain unestablished.",
        "correction": None, "fact_ids": []}
    received = {"summary": "Further evidence is needed", "findings": [finding], "play_assessments": []}
    response = {"content": json.dumps(received)[:-1] + ', "scenario_risks": [{"unfinished":',
        "id": "known-failed-generation", "error": "Upstream idle timeout exceeded",
        "error_type": "stream_error", "error_status": 504, "finish_reason": "error", "error_retryable": True,
        "usage": {"cost": 0.01}}
    return prompt, received, response


def test_complete_findings_survive_without_claiming_review_clearance():
    prompt, received, response = review_fixture()
    retained, warnings = retain_terminal_review(response, prompt, independent.validate_independent_stage)
    assert retained["findings"] == received["findings"]
    assert retained["review_completion"] == "partial"
    assert retained["review_coverage"]["assigned_scope"] == prompt["review_scope"]
    assert retained["review_coverage"]["missing_fields"] == ["evidence_requests", "market_questions", "scenario_risks"]
    assert retained["scenario_risks"] == [] and warnings
    assert not independent.validate_independent_stage(retained, prompt)
    projected = review_findings([retained])[0]
    assert projected["review_coverage"] == retained["review_coverage"]
    assert projected["review_completion"] == "partial"


def test_only_closed_members_of_an_interrupted_findings_array_are_retained():
    prompt, received, response = review_fixture()
    response["content"] = '{"summary":"review", "findings":[' + json.dumps(received["findings"][0]) + ', {"argument":"unfinished'
    retained, warnings = retain_terminal_review(response, prompt, independent.validate_independent_stage)
    assert retained["findings"] == received["findings"]
    assert retained["review_coverage"]["incomplete_fields"] == ["findings"]
    assert retained["review_completion"] == "partial" and warnings
    from backend.portfolio_recovery import completed_json_fields
    assert completed_json_fields(response["content"]) == {"summary": "review"}
    # A completed object without its array delimiter is not yet a received member.
    response["content"] = '{"findings":[' + json.dumps(received["findings"][0])
    assert retain_terminal_review(response, prompt, independent.validate_independent_stage) == (None, [])


@pytest.mark.parametrize("change", ["uncertain", "unfinished_findings", "no_findings", "invalid_finding", "delta"])
def test_incomplete_or_unconfirmed_findings_are_not_promoted(change):
    prompt, received, response = review_fixture()
    if change == "uncertain":
        response["outcome_uncertain"] = True
    elif change == "delta":
        prompt["update_contract"] = "portfolio-review-delta-v1"
    else:
        if change == "unfinished_findings":
            response["content"] = '{"summary":"review", "findings":[{"argument":"unfinished'
        else:
            received["findings"] = [] if change == "no_findings" else [{"argument": "Only part of a finding"}]
            response["content"] = json.dumps(received)
    assert retain_terminal_review(response, prompt, independent.validate_independent_stage) == (None, [])


@pytest.mark.asyncio
async def test_terminal_review_is_saved_without_repeating_paid_call_and_reused(tmp_path):
    prompt, received, response = review_fixture()
    client = AsyncMock(return_value=deepcopy(response))
    path = tmp_path / "first.checkpoint.json"
    runtime = PortfolioRuntime(path)
    messages = [{"role": "user", "content": json.dumps(prompt)}]
    options = {"parser": parse_json_object, "validator": independent.validate_independent_stage}
    result = await runtime.query(client, "model", messages, **options)
    assert client.await_count == 1 and result["stage_status"] == "complete"
    assert json.loads(result["content"])["review_completion"] == "partial"
    assert [row["status"] for row in runtime.receipts] == ["failed", "complete"]
    assert runtime.receipts[0]["raw_response"] == response
    assert runtime.receipts[1]["recovery_kind"] == "retained_terminal_review"
    summary = workload_summary(runtime.receipts)
    assert summary["new_model_requests"] == 1 and summary["retry_requests"] == 0
    assert summary["reported_openrouter_usd"] == 0.01
    resumed = PortfolioRuntime(tmp_path / "second.checkpoint.json", path)
    client.reset_mock()
    assert await resumed.query(client, "model", messages, **options) == result
    client.assert_not_awaited()
    assert workload_summary(resumed.receipts)["new_model_requests"] == 0


@pytest.mark.asyncio
async def test_old_terminal_receipt_can_be_retained_locally_but_changed_prompt_cannot(tmp_path):
    prompt, _, response = review_fixture()
    messages = [{"role": "user", "content": json.dumps(prompt)}]
    options = {"parser": parse_json_object, "validator": independent.validate_independent_stage}
    original = PortfolioRuntime(tmp_path / "old.checkpoint.json")
    await original.query(AsyncMock(return_value=response), "model", messages, **options)
    # Recreate a deployed pre-fix checkpoint: only the original failure was saved.
    original.receipts = original.receipts[:1]
    original.cache.clear()
    await original.asave()
    resumed = PortfolioRuntime(tmp_path / "new.checkpoint.json", original.checkpoint)
    client = AsyncMock(return_value={"error": "Should only be called for changed input", "error_retryable": False})
    result = await resumed.query(client, "model", messages, **options)
    client.assert_not_awaited()
    assert json.loads(result["content"])["review_completion"] == "partial"
    assert workload_summary(resumed.receipts)["new_model_requests"] == 0
    prompt["review_scope"] = {"case_ids": ["different-case"]}
    changed = PortfolioRuntime(tmp_path / "changed.checkpoint.json", original.checkpoint)
    result = await changed.query(client, "model", [{"role": "user", "content": json.dumps(prompt)}], **options)
    assert client.await_count == 1 and result["stage_status"] == "failed"


@pytest.mark.asyncio
async def test_aggregate_counts_retained_partial_separately(monkeypatch):
    monkeypatch.setattr(independent, "review_prompt_batches", lambda *args: [{"task": "one"}, {"task": "two"}])
    call = AsyncMock(side_effect=[{"stage_status": "complete", "findings": [{"argument": "complete finding"}]},
        {"stage_status": "complete", "review_completion": "partial", "review_coverage": {"missing_fields": ["scenario_risks"]},
            "findings": [{"argument": "retained finding"}], "warnings": [{"detail": "Review incomplete"}]}])
    result = await independent.run_financial_review("reviewer", "model", {}, {}, {}, {}, {}, [], call, PortfolioRuntime())
    assert result["review_completion"] == "partial" and result["stage_status"] == "complete"
    assert result["completed_review_parts"] == 1 and result["retained_partial_review_parts"] == 1
    assert len(result["findings"]) == 2 and result["warnings"]
    assert result["review_parts"][1]["review_coverage"] == {"missing_fields": ["scenario_risks"]}
    projected = review_findings([result])[0]
    assert "review_parts" not in projected
    assert len(projected["incomplete_review_parts"]) == 1
    assert projected["incomplete_review_parts"][0]["review_completion"] == "partial"


@pytest.mark.asyncio
async def test_failed_review_keeps_assigned_scope_in_reconciliation(monkeypatch):
    scope = {"case_ids": ["unassessed-gold"]}
    monkeypatch.setattr(independent, "review_prompt_batches", lambda *args: [{"review_scope": scope}])
    result = await independent.run_financial_review("reviewer", "model", {}, {}, {}, {}, {}, [],
        AsyncMock(return_value={"stage_status": "failed", "error": "timeout"}), PortfolioRuntime())
    assert result["review_completion"] == "failed"
    assert review_findings([result])[0]["review_coverage"]["assigned_scope"] == scope
