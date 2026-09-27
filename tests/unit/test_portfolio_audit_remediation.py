import json
from copy import deepcopy
from unittest.mock import AsyncMock

import pytest

import portfolio_positioning_memo as memo
from backend.portfolio_decisions import funding_ledger, build_decision, analysis_health
from backend.portfolio_independent import register_play_components, complete_play_assessments
from backend.portfolio_judgment import (
    apply_decision_revision, calculate_financial_claims, decision_checks, detail_basis,
    disposition_issues, financial_comparison_issues,
    judgment_audit, substantive_details,
)
from backend.portfolio_runtime import CURRENT_RUNTIME, PortfolioRuntime
from backend.portfolio_progress import request_phase, request_label


def target(name, weight, **fields):
    return dict(asset_class=name, min_pct=weight, max_pct=weight, target_pct=weight, **fields)


def snapshot():
    return {"portfolio": {"cash_pct": 40}, "asset_classes": [
        {"asset_class": "miners", "portfolio_pct": 40}, {"asset_class": "energy", "portfolio_pct": 20}]}


def proposal():
    return {"executive_summary": "Original decision", "asset_class_targets": [
        target("miners", 40), target("energy", 20), target("cash", 40)], "current_sleeve_actions": []}


def fact(identifier, **fields):
    return {"id": identifier, "metric": "policy rate", "benchmark": "Fed funds", "value": 4,
        "unit": "%", "currency": "USD", "observed_at": "2026-09-18",
        "measurement": {"reference_period": "2026-09-18", "price_basis": "nominal", "annualization": "annual"}, **fields}


def test_model_equivalence_cannot_erase_a_full_miner_to_bullion_switch():
    book = {"portfolio": {"cash_pct": 0}, "asset_classes": [{"asset_class": "miners", "portfolio_pct": 100}]}
    final = {"asset_class_targets": [target("bullion", 100, baseline_links=[
        {"view": "holdings", "asset_class": "miners", "relationship": "equivalent"}])],
        "current_sleeve_actions": [{"asset_class": "miners", "action": "EXIT"}, {"asset_class": "cash", "action": "HOLD"}]}
    ledger = funding_ledger(book, final)
    assert ledger["one_way_turnover_pct"] is None
    assert any("holdings record" in issue for issue in ledger["issues"])
    assert ledger["rows"][0]["current_pct"] == 0


def test_snapshot_preserves_input_identity_but_model_cannot_attest_capital():
    book = memo._compact_snapshot({"portfolio": {"cash_pct": 0}, "asset_classes": [{
        "asset_class": "miners", "portfolio_pct": 100, "implementation": {"instrument_type": "equity"},
        "aliases": ["gold_equities"], "capital_components": [{"asset_class": "producer", "share_pct": 60}]}]})
    assert book["asset_classes"][0]["implementation"]["instrument_type"] == "equity"
    final = {"asset_class_targets": [target("gold_equities", 100, baseline_links=[
        {"view": "holdings", "asset_class": "miners", "relationship": "equivalent"}])],
        "current_sleeve_actions": [{"asset_class": "cash", "action": "HOLD"}]}
    assert funding_ledger(book, final)["one_way_turnover_pct"] == 0
    final["asset_class_targets"][0].update(asset_class="unverified", baseline_links=[{
        "view": "holdings", "asset_class": "miners", "relationship": "partial_overlap", "capital_component": True, "share_pct": 100}])
    assert funding_ledger(book, final)["issues"]


@pytest.mark.asyncio
async def test_failed_refresh_never_recovers_stale_case_as_current(monkeypatch):
    old = target("bonds", 40, rationale="Falling inflation", investment_case={"downside": "Old argument"})
    evidence = {"facts": []}
    old["detail_evidence_hash"] = detail_basis(old, evidence)
    changed = {**deepcopy(old), "rationale": "Rising inflation"}
    rt = PortfolioRuntime()
    rt.query = AsyncMock(return_value={"stage_status": "failed", "content": "", "error": "Network failure"})
    token = CURRENT_RUNTIME.set(rt)
    try:
        final = await memo._refresh_final_investment_cases({"asset_class_targets": [changed]}, {"asset_class_targets": [old]}, evidence, {})
    finally:
        CURRENT_RUNTIME.reset(token)
    row = final["asset_class_targets"][0]
    assert row["detail_status"] == "needs_review"
    assert "investment_case" not in row and "detail_evidence_hash" not in row
    assert row["previous_investment_details"]["investment_case"]["downside"] == "Old argument"
    assert not substantive_details({"investment_case": {"downside": "unknown"}})


def test_empty_or_one_sided_measurement_does_not_pass_comparison():
    pair = {"facts": [fact("a", measurement={"price_basis": None}), fact("b", measurement={"price_basis": None})]}
    comparison = {"financial_comparisons": [{"left_fact_id": "a", "right_fact_id": "b"}]}
    assert financial_comparison_issues(comparison, pair)[0]["status"] == "unresolved"
    pair["facts"][0]["measurement"] = {"price_basis": "nominal", "horizon_months": 12}
    pair["facts"][1]["measurement"] = {"price_basis": "nominal"}
    assert "horizon_months" in financial_comparison_issues(comparison, pair)[0]["detail"]


def test_unrelated_percentages_and_vintages_are_not_an_economic_midpoint():
    claim = {"calculations": [{"operation": "midpoint", "fact_ids": ["a", "b"]}]}
    pair = {"facts": [fact("a", metric="GDP growth"), fact("b", metric="Treasury yield")]}
    assert calculate_financial_claims(claim, pair)[0]["computed_value"] is None
    pair = {"facts": [fact("a", value=3.75), fact("b", value=4)]}
    assert calculate_financial_claims(claim, pair)[0]["computed_value"] == 3.875
    pair["facts"][1]["observed_at"] = "2026-08-01"
    assert calculate_financial_claims(claim, pair)[0]["computed_value"] is None


def test_accepted_correction_needs_verified_current_text_not_agreement():
    final = {"executive_summary": "4% real yield", "review_dispositions": [{"finding_id": "f", "status": "accepted", "reason": "Agreed"}]}
    reviews = [{"findings": [{"id": "f", "kind": "factual_correction", "argument": "The yield is nominal"}]}]
    assert disposition_issues(final, reviews)
    final["finding_checks"] = [{"finding_id": "f", "status": "resolved", "reason": "Corrected", "path": ["executive_summary"], "quote": "4% nominal yield", "fact_ids": ["rate"]}]
    assert disposition_issues(final, reviews)
    final["executive_summary"] = "4% nominal yield"
    assert judgment_audit(final, reviews, {"facts": [fact("rate")]})["unresolved_findings"]
    from backend.portfolio_evidence import apply_fact_checks, review_fields
    packet = {"as_of": "2026-09-21", "sources": [{"id": "s", "excerpt": "4% nominal yield"}]}
    observation = fact("rate", kind="market_price", source_ids=["s"], source_excerpt="4% nominal yield")
    verified = apply_fact_checks([observation],
        [{"fact_id": "rate", "checks": {key: "supported" for key in review_fields(observation)}, "reason": "Nominal yield is explicitly stated"}], packet)
    assert not judgment_audit(final, reviews, {"facts": verified})["unresolved_findings"]
    assert judgment_audit(final, reviews, {"facts": []})["unresolved_findings"]


def test_play_manifest_retains_every_component_and_missing_ones_are_explicit():
    plays = [{"id": "p", "title": "Scarcity", "thesis": "Fertiliser, gold miners, silver miners, oil producers, uranium producers"}]
    names = ["Fertiliser", "gold miners", "silver miners", "oil producers", "uranium producers"]
    reviews = [{"play_assessments": [{"play_id": "p", "legs": [{"name": name, "source_text": name} for name in names]}]}]
    registered = register_play_components(plays, reviews)
    assert len(registered[0]["components"]) == 5
    assessment = complete_play_assessments(registered, [{"play_id": "p", "score": 8, "verdict": "include", "legs": [{
        "component_id": registered[0]["components"][0]["id"], "mechanism": "Supply constraint", "verdict": "watch", "score": 6}]}])[0]
    assert len(assessment["legs"]) == 5
    assert sum(row.get("assessment_status") == "missing" for row in assessment["legs"]) == 4
    assert assessment["coverage_status"] == "incomplete"
    missing = complete_play_assessments(register_play_components(plays, []), [{"play_id": "p", "score": 8, "verdict": "include"}])[0]
    assert missing["score"] is None and missing["coverage_status"] == "incomplete"


def test_lower_turnover_alternative_is_checked_before_selection():
    final = proposal()
    final["smaller_change_alternative"] = {"asset_class_targets": [target("miners", 0), target("energy", 0), target("cash", 100)]}
    checks = decision_checks(snapshot(), final, [], {"facts": []})
    assert checks["implementation_comparison"]["issues"]


def test_scoped_decision_revision_changes_only_funded_affected_rows():
    original = proposal()
    response = {"stage_status": "complete", "reason": "Operating margins change the miner case", "executive_summary": "Reduce miners; retain cash pending better margins",
        "target_updates": [target("miners", 30), target("cash", 50)]}
    scope = {"asset_classes": ["MINERS", "CASH"]}
    result = apply_decision_revision(original, response, scope, snapshot())
    assert result["decision_reconsideration"]["changed"]
    assert result["asset_class_targets"][1] == original["asset_class_targets"][1]
    assert funding_ledger(snapshot(), result)["status"] == "balanced"
    assert original == proposal()
    for bad in ([target("miners", 20)], [target("energy", 10), target("cash", 50)]):
        result = apply_decision_revision(original, {**response, "target_updates": bad}, scope, snapshot())
        assert [{k: v for k, v in row.items() if k != "decision_review_status"} for row in result["asset_class_targets"]] == original["asset_class_targets"]
        assert result["decision_reconsideration"]["status"] == "unresolved"


def test_failed_decision_revision_retains_the_original_and_qualifies_only_scope():
    result = apply_decision_revision(proposal(), {"stage_status": "failed", "error": "Provider unavailable"}, {"asset_classes": ["MINERS"]}, snapshot())
    assert [row["target_pct"] for row in result["asset_class_targets"]] == [40, 20, 40]
    assert result["asset_class_targets"][0]["decision_review_status"] == "unresolved"
    assert "decision_review_status" not in result["asset_class_targets"][1]
    decision = build_decision(snapshot(), result, {"facts": []})
    assert any("material correction" in item for item in decision["funding"]["rows"][0]["open_questions"])
    assert not any("material correction" in item for item in decision["funding"]["rows"][1]["open_questions"])
    health = analysis_health({"workflow_version": 3, "portfolio_snapshot": snapshot(), "macro_positioning": result,
        "independent_ideal": proposal(), "current_portfolio_assessment": {"executive_summary": "Current view"}})
    assert health["status"] == "complete"
    assert any(row["stage"] == "decision review" for row in health["warnings"])


def test_failed_malformed_revision_is_not_interpreted_as_a_patch():
    result = apply_decision_revision(proposal(), {"stage_status": "failed", "reason": "Incomplete", "target_updates": "bad", "play_assessments": [None]}, {"asset_classes": ["MINERS"]}, snapshot())
    assert result["decision_reconsideration"]["status"] == "unresolved"
    assert [row["target_pct"] for row in result["asset_class_targets"]] == [40, 20, 40]


def test_conditional_repair_has_specific_progress_labels():
    prompt = {"contract": "independent-portfolio-v1"}
    assert request_phase(prompt, "decision_reconsideration") == "synthesis"
    assert request_phase(prompt, "memo_commentary_after_reconsideration") == "commentary"
    assert request_label(prompt, "decision_reconsideration", "synthesis") == "Reconsidering affected decisions"


@pytest.mark.asyncio
async def test_successful_detail_refresh_is_reused_without_another_call():
    rt = PortfolioRuntime()
    rt.query = AsyncMock(return_value={"stage_status": "complete", "content": json.dumps({"allocation_details": [{
        "asset_class": "miners", "investment_case": {"downside": "Operating cost sensitivity"}, "implementation": {}, "market_pricing": {}, "alternatives": []}]})})
    token = CURRENT_RUNTIME.set(rt)
    try:
        first = await memo._refresh_final_investment_cases({"asset_class_targets": [target("miners", 40)]}, {}, {"facts": []}, {})
        second = await memo._refresh_final_investment_cases({"asset_class_targets": [target("miners", 40)]}, first, {"facts": []}, {})
    finally:
        CURRENT_RUNTIME.reset(token)
    assert rt.query.await_count == 1
    assert second["asset_class_targets"][0]["detail_status"] == "current"
    assert second["asset_class_targets"][0]["detail_evidence_hash"] == first["asset_class_targets"][0]["detail_evidence_hash"]
