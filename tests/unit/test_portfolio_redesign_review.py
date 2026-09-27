"""Regression tests for the independent September 21 audit counterexamples."""

from copy import deepcopy
import json
from unittest.mock import AsyncMock

import pytest

from backend.portfolio_evidence import validate_stage
from backend.portfolio_independent import review_prompt_batches
from backend.portfolio_judgment import detail_basis, retain_current_details
from backend.portfolio_recovery import completed_json_fields, parse_json_object
from backend.portfolio_runtime import CURRENT_RUNTIME, PortfolioRuntime
from backend.portfolio_tasks import evidence_for_decisions, investment_details


def evidence():
    return {"facts": [{"id": "support", "metric": "Margin", "benchmark": "Producer", "unit": "USD/t",
                       "value": 200, "source_ids": ["source"], "source_excerpt": "Margin 200"}],
            "source_packet": {"sources": [{"id": "source", "url": "https://example.test/report"}]},
            "research_questions": [{"id": "economics", "question": "What are producer economics?",
                "asset_classes": ["producer"], "answers": [{"dimension": "margin", "answer": "200",
                                                           "fact_ids": ["support"]}]}]}


def test_new_case_evidence_invalidates_retained_detail():
    before = evidence()
    target = {"asset_class": "producer", "target_pct": 10, "rationale": "Margins support the case",
              "fact_ids": ["support"], "research_question_ids": ["economics"],
              "investment_case": {"why_better_than_hold": "Margins"}, "detail_status": "current"}
    target["detail_evidence_hash"] = detail_basis(target, before)
    saved = investment_details({"asset_class_targets": [target]})
    after = deepcopy(before)
    after["facts"].append({**after["facts"][0], "id": "contrary", "metric": "Cost", "value": 300,
                           "source_excerpt": "Costs 300"})
    after["research_questions"][0]["answers"].append(
        {"dimension": "cost", "answer": "Costs exceed margins", "fact_ids": ["contrary"]})
    assert "contrary" in {row["id"] for row in evidence_for_decisions(after, [target])["facts"]}
    final, stale = retain_current_details({"asset_class_targets": [target]}, saved, after)
    assert stale and final["asset_class_targets"][0]["detail_status"] == "needs_review"


@pytest.mark.asyncio
async def test_changed_case_receives_complete_book_weights(tmp_path):
    from scripts import portfolio_positioning_memo as memo
    raw = evidence()
    cash = {"asset_class": "cash", "target_pct": 90, "rationale": "Liquidity",
            "investment_case": {"why_better_than_hold": "Liquidity"}, "detail_status": "current"}
    cash["detail_evidence_hash"] = detail_basis(cash, raw)
    final = {"asset_class_targets": [{"asset_class": "producer", "target_pct": 10}, cash]}
    runtime = PortfolioRuntime(tmp_path / "weights.json")
    runtime.query = AsyncMock(return_value={"stage_status": "complete", "content": '{"allocation_details":[]}'} )
    token = CURRENT_RUNTIME.set(runtime)
    try:
        await memo._refresh_final_investment_cases(final, investment_details(final), raw, {})
    finally:
        CURRENT_RUNTIME.reset(token)
    assert runtime.query.await_count == 1
    prompt = json.loads(runtime.query.call_args.args[2][0]["content"])
    assert sum(row["target_pct"] for row in prompt["recorded_allocation"]) == 100


def test_play_only_research_does_not_omit_unlinked_baseline_target():
    raw = evidence()
    raw["research_questions"][0]["play_ids"] = ["p"]
    ideal = {"asset_class_targets": [{"asset_class": "cash", "target_pct": 90, "rationale": "Liquidity"},
                                    {"asset_class": "producer", "target_pct": 10, "fact_ids": ["support"]}]}
    parts = review_prompt_batches("defensive_regime_reviewer", raw, {"research_cutoff": "2026-09-20"},
                                  ideal, {}, {}, [{"id": "p", "title": "Producer", "thesis": "Scarcity"}], packet_chars=1)
    covered = {row["asset_class"] for part in parts for row in part["independent_ideal"]["asset_class_targets"]}
    assert covered == {"cash", "producer"}


def test_split_review_preserves_current_exit_argument():
    current = {"asset_class_targets": [{"asset_class": "cash", "target_pct": 100}],
               "current_assessment": [{"asset_class": "producer", "action": "EXIT", "rationale": "Cost impairment"}]}
    parts = review_prompt_batches("defensive_regime_reviewer", evidence(), {"research_cutoff": "2026-09-20"},
                                  {}, current, {}, [], packet_chars=1)
    assessments = [row for part in parts for row in part["current_assessment"].get("current_assessment", [])]
    assert any(row["asset_class"] == "producer" and row["action"] == "EXIT" for row in assessments)


def test_partial_numeric_token_is_not_a_received_financial_value():
    assert completed_json_fields('{"summary":"saved","score":1e') == {"summary": "saved"}


@pytest.mark.asyncio
async def test_confirmed_credit_rejection_can_resume_after_topup(tmp_path, monkeypatch):
    from backend import portfolio_funding as funding
    monkeypatch.setattr(funding, "funding_snapshot", AsyncMock(return_value={
        "available_usd": 10, "prices": {"model": {"prompt": 0, "completion": 0}}}))
    calls = []
    async def client(*args, **kwargs):
        calls.append(args)
        if len(calls) == 1:
            return {"error_status": 402, "error": "Insufficient credits", "content": ""}
        return {"content": '{"answer":"saved"}', "finish_reason": "stop"}
    client.supports_progress = True
    runtime = PortfolioRuntime(tmp_path / "original.checkpoint.json")
    runtime.funding_guard = funding.FundingGuard()
    messages = [{"role": "user", "content": json.dumps({"task": "Audit", "required_schema": {"answer": "string"}})}]
    with pytest.raises(funding.FundingRequired):
        await runtime.query(client, "model", messages, parser=parse_json_object, validator=validate_stage)
    resumed = PortfolioRuntime(tmp_path / "resumed.checkpoint.json", runtime.checkpoint)
    resumed.funding_guard = funding.FundingGuard()
    result = await resumed.query(client, "model", messages, parser=parse_json_object, validator=validate_stage)
    assert result["stage_status"] == "complete" and len(calls) == 2


def test_new_extraction_task_is_counted_as_extraction():
    from backend.portfolio_funding import work_kind
    assert work_kind("macro_regime:Extract dated observations from source snapshots") == "extract"
