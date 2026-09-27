"""Failure-boundary regressions from the second uplift audit; no paid calls."""

import asyncio
from copy import deepcopy
from unittest.mock import AsyncMock

import pytest

from backend.portfolio_decisions import evaluate_conditions, funding_ledger
from backend.portfolio_evidence import (
    apply_fact_checks, fact_observation_is_supported, merge_briefs, review_fields, validate_stage, FACT_CHECK_SCHEMA,
)
from backend.portfolio_independent import (
    complete_play_assessments, component_inventory_verified, decision_document,
    establish_play_components, freeze_play_components, register_play_components,
)
from backend.portfolio_judgment import apply_claim_patches, claim_patch_paths, decision_checks, implementation_comparison
from backend.portfolio_recovery import merge_reviews, recover_reviews
from backend.portfolio_research import restore_phase_research
from backend.portfolio_runtime import CURRENT_RUNTIME, PortfolioRuntime
from backend.portfolio_tasks import evidence_for_decisions
from scripts import portfolio_positioning_memo as memo
from scripts.audit_portfolio_uplift_second_pass import audit, source_case


@pytest.fixture(scope="module")
def original_audit():
    return {row["id"]: row for row in asyncio.run(audit())}


@pytest.mark.parametrize("identifier", [f"R{number:02d}" for number in range(1, 10)])
def test_original_audit_counterexamples(identifier, original_audit):
    result = original_audit[identifier]
    assert result["passed"], result


def review(fact, **updates):
    return {"fact_id": fact["id"], "checks": {key: "supported" for key in review_fields(fact)},
            "reason": "The supplied source supports these fields.", **updates}


@pytest.mark.parametrize("field,extra", [
    ("reference_period", {"observation_type": "period_statistic", "reference_period": "2026-Q2"}),
    ("target_period", {"observation_type": "forecast", "target_period": "2027"}),
    ("measurement.maturity_months", {"measurement": {"maturity_months": 120}}),
    ("applicability.instrument", {"applicability": {"instrument": "upstream producers"}}),
    ("locator.column", {"locator": {"column": "August 2026"}}),
])
def test_typed_fields_share_validation_recovery_and_support_contract(field, extra):
    packet, fact = source_case()
    fact.update(extra)
    verdict = review(fact)
    prompt = {"required_schema": {"fact_checks": FACT_CHECK_SCHEMA}, "evidence": {"facts": [fact]}}
    verdict["checks"].pop(field)
    assert any(field in error for error in validate_stage({"fact_checks": [verdict]}, prompt))
    retained, warnings = recover_reviews({"fact_checks": [verdict]}, prompt)
    assert warnings and retained["fact_checks"][0]["checks"][field] == "unresolved"
    assert not fact_observation_is_supported(apply_fact_checks([fact], retained["fact_checks"], packet)[0])
    verdict["checks"][field] = "unsupported"
    bad = apply_fact_checks([fact], [verdict], packet)[0]
    assert bad["claim_status"] == "unsupported" and not fact_observation_is_supported(bad)
    verdict["checks"][field] = "supported"
    assert fact_observation_is_supported(apply_fact_checks([fact], [verdict], packet)[0])


def test_review_repair_preserves_corrections_and_does_not_invent_missing_metadata():
    packet, fact = source_case()
    fact.update(observation_type="period_statistic", reference_period="2026-08", observed_at=None,
                published_at=None, vintage=None)
    checks = review(fact)
    checks["checks"].update(observed_at="not_applicable", published_at="unresolved", vintage="not_applicable", value="unsupported")
    correction = review(fact)["checks"]
    correction.update(observed_at="not_applicable", published_at="unresolved", vintage="not_applicable")
    checks["correction"] = {"changes": {"value": 90.9}, "checks": correction, "reason": "August column"}
    prompt = {"evidence": {"facts": [fact]}}
    repaired = merge_reviews(None, {"fact_checks": [checks]}, prompt)
    retained, _ = recover_reviews(repaired, prompt)
    result = apply_fact_checks([fact], retained["fact_checks"], packet)
    assert len(result) == 2 and fact_observation_is_supported(result[1])
    assert result[1]["published_at"] is None


@pytest.mark.parametrize("raw_first", [True, False])
def test_supersession_and_review_survive_merge_order_and_recovery(raw_first):
    packet, fact = source_case()
    check = review(fact)
    check["checks"]["value"] = "unsupported"
    check["correction"] = {"changes": {"value": 90.9}, "checks": review(fact)["checks"], "reason": "August column"}
    corrected = {"facts": apply_fact_checks([fact], [check], packet), "source_packet": packet}
    raw = {"facts": [fact], "source_packet": packet}
    parts = [raw, corrected] if raw_first else [corrected, raw]
    merged = merge_briefs(parts)
    old = next(row for row in merged["facts"] if row["value"] == 82.6)
    new = next(row for row in merged["facts"] if row["value"] == 90.9)
    assert old["superseded_by"] == new["id"] and new["supersedes"] == old["id"]
    assert not fact_observation_is_supported(old) and fact_observation_is_supported(new)
    saved = {"targeted_research_results": {"challenge:old": {"phase": "challenge", "evidence_brief": raw}}}
    recovered, _ = restore_phase_research(merged, saved, "challenge")
    assert next(row for row in recovered["facts"] if row["value"] == 82.6)["superseded_by"] == new["id"]


def test_changed_source_snapshot_cannot_inherit_a_supported_review():
    packet, fact = source_case()
    verified = apply_fact_checks([fact], [review(fact)], packet)
    changed = deepcopy(packet)
    changed["sources"][0]["excerpt"] = "A revised report with no Brent prices."
    merged = merge_briefs([{"facts": verified, "source_packet": packet}, {"facts": [fact], "source_packet": changed}])
    assert not fact_observation_is_supported(merged["facts"][0])
    assert merged["facts"][0]["claim_status"] == "unresolved"


def test_canonical_ids_keep_correction_chain_in_scoped_evidence():
    packet, fact = source_case()
    fact["id"] = "original"
    check = review(fact)
    check["checks"]["value"] = "unsupported"
    check["correction"] = {"changes": {"value": 90.9}, "checks": review(fact)["checks"], "reason": "August column"}
    first = apply_fact_checks([fact], [check], packet)
    last = deepcopy(first[1])
    last.update(id="final", metric="Corrected Brent series", supersedes=first[1]["id"])
    first[1]["superseded_by"] = "final"
    merged = merge_briefs([{"facts": [*first, last], "source_packet": packet}])
    projected = evidence_for_decisions(merged, {"fact_ids": ["original"]})
    assert len(projected["facts"]) == 3
    ids = {row["id"] for row in merged["facts"]}
    assert all(row.get("supersedes", row["id"]) in ids and row.get("superseded_by", row["id"]) in ids for row in merged["facts"])


def test_explicit_forecast_without_target_period_remains_usable_but_unverified():
    packet, fact = source_case()
    fact.update(kind="forecast", observation_type="forecast", observed_at=None)
    checked = apply_fact_checks([fact], [review(fact)], packet)[0]
    assert checked["value"] == 82.6
    assert not fact_observation_is_supported(checked)
    assert "Missing target_period" in checked["verification_issues"]


def idea():
    return {"id": "p", "title": "Scarcity", "thesis": "Fertiliser and uranium producers"}


def component(name):
    return {"name": name, "economic_key": name, "source_text": name, "direction": "long"}


def inventory(names, **updates):
    return [{"play_id": "p", "components": [component(name) for name in names],
        "coverage_status": "complete", "coverage_reason": "Both explicit subjects have their own component.",
        "unresolved_source_text": [], **updates}]


@pytest.mark.asyncio
async def test_partial_inventory_is_repaired_once_and_checked_receipt_is_reusable():
    partial = inventory(["Fertiliser"], coverage_status="incomplete", unresolved_source_text=["uranium producers"])
    call = AsyncMock(return_value={"play_components": inventory(["Fertiliser", "uranium producers"])})
    result = await establish_play_components([idea()], partial, call, "mock/model", "2026-09-21")
    assert call.await_count == 1 and component_inventory_verified(result[0])
    again = await establish_play_components(result, None, call, "mock/model", "2026-09-21")
    assert call.await_count == 1 and again == result
    result[0]["thesis"] += " and silver miners"
    assert not component_inventory_verified(result[0])


@pytest.mark.asyncio
async def test_failed_inventory_repair_retains_components_without_claiming_completeness():
    partial = inventory(["Fertiliser"], coverage_status="incomplete", unresolved_source_text=["uranium producers"])
    call = AsyncMock(return_value={"stage_status": "failed", "error": "Unavailable"})
    result = await establish_play_components([idea()], partial, call, "mock/model", "2026-09-21")
    assert result[0]["components"] and not component_inventory_verified(result[0])
    assert complete_play_assessments(result, [])[0]["coverage_status"] == "incomplete"


def test_late_source_grounded_component_invalidates_completeness_receipt():
    frozen = freeze_play_components([idea()], inventory(["Fertiliser"]))
    assert component_inventory_verified(frozen[0])
    rows = [{"play_assessments": [{"play_id": "p", "legs": [{"name": "uranium producers", "source_text": "uranium producers"}]}]}]
    result = register_play_components(frozen, rows)
    assert len(result[0]["components"]) == 2
    assert not component_inventory_verified(result[0])
    assert complete_play_assessments(result, [])[0]["coverage_status"] == "incomplete"


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["discovery", "extraction"])
async def test_partial_inspection_survives_failures_and_resume_without_losing_missing_dimension(tmp_path, monkeypatch, failure):
    packet, fact = source_case()
    async def structure(lane, **kwargs):
        if not lane.get("source_inspection"):
            raise RuntimeError("Extraction unavailable")
        lane["evidence_brief"] = {"facts": [fact], "source_packet": packet, "question_answers": [
            {"dimension": "price", "status": "answered", "answer": "Price established", "fact_ids": [fact["id"]]}]}
        return lane
    provider = AsyncMock(side_effect=RuntimeError("Discovery unavailable")) if failure == "discovery" else AsyncMock(
        return_value={"results": [{"url": "https://example.test/new", "content": "Supplementary source"}]})
    monkeypatch.setattr(memo, "_structure_evidence_lane", structure)
    monkeypatch.setattr(memo.ParallelSourceProvider, "gather", provider)
    rt = PortfolioRuntime(tmp_path / "checkpoint.json")
    token = CURRENT_RUNTIME.set(rt)
    try:
        evidence, _, report = await memo._run_question_research({"facts": [], "source_packet": packet}, "deep", {
            "phase": "challenge", "questions": [{"question": "Price and costs?", "required_dimensions": ["price", "costs"],
                "asset_classes": ["energy"], "inspect_source_ids": ["s"], "material_reason": "Margins", "reuse_assessment": "Read report"}]})
    finally:
        CURRENT_RUNTIME.reset(token)
    assert evidence["facts"] and report["questions"][0]["status"] == "partial"
    recovered, _ = restore_phase_research({"facts": [], "source_packet": packet}, rt.partial, "challenge")
    assert recovered["facts"]
    question = recovered["research_questions"][0]
    assert "costs" in question["missing_dimensions"] and "costs" not in question.get("searched_dimensions", [])


def test_funding_flow_reaches_existing_reviewer_without_invalidating_balanced_arithmetic():
    snapshot = {"portfolio": {"cash_pct": 50}, "asset_classes": [{"asset_class": "gold", "portfolio_pct": 50}]}
    proposal = {"asset_class_targets": [{"asset_class": "gold", "target_pct": 60, "funding_from": ["gold"]},
                                      {"asset_class": "cash", "target_pct": 40}]}
    ledger = funding_ledger(snapshot, proposal)
    assert ledger["status"] == "balanced" and ledger["funding_flow_status"] == "unresolved"
    checked = decision_checks(snapshot, proposal, [], {})
    assert checked["judgment_audit"]["funding_flow_issues"] and checked["implementation_comparison"]["issues"]


def test_document_walk_covers_financial_prose_but_never_numeric_or_identity_fields():
    document = decision_document({"executive_summary": "View", "current_sleeve_actions": [
        {"asset_class": "bonds", "target_pct": 10, "action": "TRIM", "rationale": "Case"}],
        "scenario_risks": [{"name": "Rates", "assumptions": [{"claim": "Higher yields", "basis": "hypothetical", "fact_ids": ["f"]}]}],
        "research_assessment": [{"question_id": "q", "implication": "Changed case", "portfolio_consequence": "Retain"}],
        "mandate_review": {"tax_cost_policy": {"policy": "original", "status": "unassessed", "reason": "Unknown"}}})
    paths = {tuple(row["path"]) for row in claim_patch_paths(document)}
    for path in [("executive_summary",), ("current_sleeve_actions", 0, "rationale"),
                 ("scenario_risks", 0, "assumptions", 0, "claim"), ("research_assessment", 0, "implication"),
                 ("research_assessment", 0, "portfolio_consequence"), ("mandate_review", "tax_cost_policy", "reason")]:
        assert path in paths
    assert not any(path[-1] in {"asset_class", "target_pct", "action", "name", "basis", "policy", "status", "question_id"} for path in paths)
    stale = apply_claim_patches(document, {"patches": [{"path": ["current_sleeve_actions", 0, "rationale"],
        "original": "Outdated", "replacement": "New", "reason": "Correction"}]})
    assert stale["current_sleeve_actions"][0]["rationale"] == "Case"


def test_checker_cannot_patch_an_archived_case_it_was_not_given():
    proposal = {"asset_class_targets": [{"asset_class": "bonds", "target_pct": 10, "rationale": "Current",
        "previous_investment_details": {"investment_case": {"downside": "Archived original"}}}]}
    path = ["asset_class_targets", 0, "previous_investment_details", "investment_case", "downside"]
    assert tuple(path) not in {tuple(row["path"]) for row in claim_patch_paths(proposal)}
    result = apply_claim_patches(proposal, {"patches": [{"path": path, "original": "Archived original", "replacement": "Rewritten", "reason": "Not permitted"}]})
    assert not result["claim_corrections"]
    assert result["asset_class_targets"][0]["previous_investment_details"]["investment_case"]["downside"] == "Archived original"


def test_mixed_scenario_keeps_computed_values_and_qualitative_rows():
    snapshot = {"portfolio": {"cash_pct": 50}, "asset_classes": [{"asset_class": "bonds", "portfolio_pct": 50}],
        "mandate": {"base_currency": "USD"}, "scenarios": [{"name": "Rates", "shocks": {"rates": 1}, "horizon_months": 12}],
        "risk_exposures": {"cash": {"sensitivities": {"rates": 0}, "annual_carry_pct": 4, "transaction_cost_bps": 0,
            "basis": "Cash carry", "source": "snapshot", "currency": "USD"}}}
    proposal = {"asset_class_targets": [{"asset_class": "cash", "target_pct": 50}, {"asset_class": "bonds", "target_pct": 50}],
        "scenario_risks": [{"name": "Rates", "exposures": [{"asset_class": "bonds", "direction": "harm", "reason": "Duration risk"}]}]}
    result = implementation_comparison(snapshot, proposal, {})["destination"]["scenarios"][0]
    assert result["status"] == "mixed" and result["proposed_return_pct"] is None
    rows = {row["asset_class"]: row for row in result["rows"]}
    assert rows["cash"]["return_pct"] == 4
    assert rows["bonds"]["return_pct"] is None and rows["bonds"]["direction"] == "harm"


def test_monitoring_rejects_conflicts_at_an_earlier_required_point_and_unknown_timezone():
    condition = {"metric": "yield", "benchmark": "Treasury", "unit": "%", "operator": "gt", "threshold": 4,
                 "consecutive_count": 2, "max_gap_days": 2, "max_age_days": 7}
    def observation(day, value):
        return {"metric": "yield", "benchmark": "Treasury", "unit": "%", "value": value,
            "observed_at": f"2026-09-{day}T10:00:00Z", "published_at": f"2026-09-{day}T11:00:00Z", "source_url": "https://example.test"}
    rows = [observation(20, 5), observation(19, 5), observation(19, 3)]
    result = evaluate_conditions([condition], rows, "2026-09-21T12:00:00Z")[0]
    assert result["status"] == "unassessed" and "Conflicting" in result["reason"]
    rows = rows[:2]
    assert evaluate_conditions([condition], rows, "2026-09-21T12:00:00Z")[0]["status"] == "triggered"
    rows[1]["observed_at"] = rows[1]["observed_at"].removesuffix("Z")
    assert evaluate_conditions([condition], rows, "2026-09-21T12:00:00Z")[0]["status"] == "unassessed"
