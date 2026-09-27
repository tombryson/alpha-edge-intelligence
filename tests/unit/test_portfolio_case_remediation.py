from copy import deepcopy

from backend.portfolio_independent import review_prompt_batches
from backend.portfolio_judgment import financial_case_issues, play_expression_issues


def test_same_exposure_is_one_review_case_across_baselines_actions_and_play():
    target = {"asset_class": "gold_miners", "target_pct": 10, "rationale": "Cash generation"}
    ideal = {"asset_class_targets": [target]}
    current = {"asset_class_targets": [target], "current_assessment": [{"asset_class": "GOLD_MINERS", "action": "TRIM"}]}
    plays = [{"id": "p", "title": "Scarcity", "components": [{"id": "c", "name": "Gold miners", "direction": "long", "purpose": "return"}]}]
    original = deepcopy((ideal, current, plays))
    parts = review_prompt_batches("reviewer", {"facts": [], "source_packet": {"sources": []}},
                                  {"research_cutoff": "2026-09-22"}, ideal, current, {}, plays, packet_chars=1)
    assert len(parts) == 1
    assert len(parts[0]["review_scope"]["economic_cases"]) == 1
    assert len(parts[0]["review_scope"]["economic_cases"][0]["members"]) == 4
    assert (ideal, current, plays) == original


def test_relative_hedge_dimensions_remain_together_without_erasing_components():
    plays = [{"id": "p", "components": [
        {"id": "gold", "name": "Bullion", "purpose": "hedge", "direction": "long"},
        {"id": "bonds", "name": "Nominal duration", "purpose": "hedge", "direction": "relative_preference"},
        {"id": "debt", "name": "Fiscal confidence", "purpose": "other", "direction": "other"}]}]
    parts = review_prompt_batches("reviewer", {"facts": []}, {"research_cutoff": "2026-09-22"}, {}, {}, {}, plays, packet_chars=1)
    assert len(parts) == 1
    assert {c["id"] for c in parts[0]["investment_plays"][0]["components"]} == {"gold", "bonds", "debt"}


def test_missing_economics_does_not_invent_adverse_evidence_or_move_weights():
    proposal = {"asset_class_targets": [{"asset_class": "producer", "target_pct": 12,
        "investment_case": {"causal_chain": [{"link": "price to free cash flow", "basis": "unresolved"}]}}]}
    original = deepcopy(proposal)
    result = financial_case_issues(proposal, {})
    assert result[0]["unknown_links"] == ["price to free cash flow"]
    assert "conditional" in result[0]["weight_action"]
    assert proposal == original


def test_corrected_premise_requires_new_sizing_argument_and_observed_links_need_sources():
    target = {"asset_class": "tips", "target_pct": 25, "fact_ids": ["wrong"], "investment_case": {
        "causal_chain": [{"link": "inflation to excess return", "basis": "observed", "fact_ids": []}]}}
    result = financial_case_issues({"asset_class_targets": [target]}, {"facts": [{"id": "wrong", "superseded_by": "right"}]})
    assert result[0]["changed_fact_ids"] == ["wrong"]
    assert result[0]["unsubstantiated_observed_links"] == ["inflation to excess return"]
    assert any("premise changed" in reason for reason in result[0]["reasons"])


def test_wrong_bond_expression_cannot_silently_borrow_infrastructure_identity():
    proposal = {"asset_class_targets": [{"asset_class": "infrastructure", "display_name": "Listed infrastructure"}],
        "play_assessments": [{"play_id": "hedge", "expressions": [{"asset_class": "infrastructure", "display_name": "Avoid long-maturity nominal sovereigns"}]}]}
    issue = play_expression_issues(proposal)[0]
    assert issue["status"] == "identity_needs_review"
    assert issue["target_label"] == "Listed infrastructure"
    proposal["play_assessments"][0]["expressions"][0]["display_name"] = "Listed infrastructure"
    assert play_expression_issues(proposal) == []
