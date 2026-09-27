import json
from copy import deepcopy
from unittest.mock import AsyncMock

import pytest

import portfolio_positioning_memo as memo
from backend.portfolio_decisions import funding_ledger
from backend.portfolio_evidence import merge_briefs, validate_stage, fact_fingerprint
from backend.portfolio_exposures import reconcile_references, reference_links
from backend.portfolio_independent import independent_context, allocation_prompt, complete_play_assessments
from backend.portfolio_judgment import (
    apply_claim_patches, calculate_financial_claims, detail_basis, financial_comparison_issues,
    implementation_comparison, judgment_audit, linked_facts, prepare_reviews, research_questions,
    resolve_fact_aliases, retain_current_details,
    play_outcomes,
)
from backend.portfolio_repair import load_frozen_baselines
from backend.portfolio_retrieval import FollowupBudget
from backend.portfolio_runtime import PortfolioRuntime
from backend.portfolio_memo import render_portfolio_memo


def target(name, weight, **fields):
    return dict(asset_class=name, min_pct=weight, max_pct=weight, target_pct=weight, **fields)


def fact(identifier="f1", **fields):
    return dict(id=identifier, kind="observed_macro", metric="Policy rate", value=3.75, unit="%",
                benchmark="Federal funds", currency="USD", observed_at="2026-09-18", published_at="2026-09-18",
                vintage="September", source_ids=["s1"], source_excerpt="3.75%", **fields)


@pytest.mark.asyncio
@pytest.mark.parametrize("word", ["structured-outputs", "structured_outputs", "structured outputs"])
async def test_ling_provider_format_failure_retries_same_model(word):
    client = AsyncMock(side_effect=[{"error_status": 400, "error": "Provider error", "error_type": "http_error",
        "error_body": json.dumps({"error": {"message": f"model does not support feature: {word}"}})},
        {"content": '{"summary":"A substantive financial review"}', "provider": "Novita", "model": "resolved/model"}])
    runtime = PortfolioRuntime()
    model = "inclusionai/ling-3.0-flash-fin:free"
    result = await runtime.query(client, model, [{"role": "user", "content": json.dumps({
        "task": "Review", "required_schema": {"summary": "string"}})}], parser=memo._extract_json_object, validator=validate_stage)
    assert result["stage_status"] == "complete"
    assert [call.args[0] for call in client.call_args_list] == [model, model]
    assert client.call_args_list[0].kwargs["response_format"] == {"type": "json_object"}
    assert "response_format" not in client.call_args_list[1].kwargs
    assert runtime.receipts[-1]["resolved_model"] == "resolved/model"
    assert runtime.receipts[0]["raw_response"]["error_body"]


def test_observation_identity_survives_source_metadata_refresh():
    first = merge_briefs([{"facts": [fact()]}])
    identifier = first["facts"][0]["id"]
    refreshed = deepcopy(first)
    refreshed["facts"][0].update(source_digest="new-source", source_ids=["s2"], source_excerpt="Updated document: 3.75%")
    result = merge_briefs([first, refreshed])
    assert result["facts"][0]["id"] == identifier
    assert result["facts"][0]["source_ids"] == ["s1", "s2"]
    assert len(result["facts"][0]["source_variants"]) == 2
    assert fact_fingerprint(result["facts"][0]) != fact_fingerprint(first["facts"][0])
    assert resolve_fact_aliases({"fact_ids": ["f1"]}, result)["fact_ids"] == [identifier]


def test_colliding_lane_ids_are_relinked_locally_not_globally():
    other = fact()
    other["value"] = 4
    merged = merge_briefs([{"facts": [fact()], "watchpoints": [{"fact_ids": ["f1"]}]},
                           {"facts": [other], "watchpoints": [{"fact_ids": ["f1"]}]}])
    assert len(merged["facts"]) == 2
    assert "f1" not in merged["fact_aliases"]
    assert {row["fact_ids"][0] for row in merged["watchpoints"]} == {row["id"] for row in merged["facts"]}


def test_cash_alias_uses_declared_equivalence_and_computes_baseline():
    proposal = {"asset_class_targets": [target("CASH", 20, baseline_links=[
        {"view": "ideal", "asset_class": "cash_and_equivalents", "relationship": "equivalent"}])],
        "reconciliation": [{"asset_class": "CASH", "ideal_reference_pct": 99}]}
    result = reconcile_references(proposal, {"asset_class_targets": [target("cash_and_equivalents", 12)]}, {})
    assert result["reconciliation"][0]["ideal_reference_pct"] == 12
    assert result["reconciliation"][0]["reported_references"]["ideal_reference_pct"] == 99
    assert proposal["reconciliation"][0]["ideal_reference_pct"] == 99


def test_bullion_is_not_equivalent_to_miner_equity():
    proposal = {"asset_class_targets": [target("bullion", 10, implementation={"instrument_type": "physical bullion"},
        baseline_links=[{"view": "ideal", "asset_class": "miners", "relationship": "equivalent"}])]}
    links, issues = reference_links(proposal, "ideal", [target("miners", 20, implementation={"instrument_type": "equity"})])
    assert not links["BULLION"]
    assert issues
    proposal["asset_class_targets"][0]["baseline_links"][0]["relationship"] = "substitute"
    assert reference_links(proposal, "ideal", [target("miners", 20)])[0]["BULLION"] == []


def test_partial_overlap_funding_never_duplicates_capital():
    snapshot = {"portfolio": {"cash_pct": 0}, "asset_classes": [{"asset_class": "book", "portfolio_pct": 100,
        "capital_components": [{"asset_class": "part_a", "share_pct": 40}, {"asset_class": "part_b", "share_pct": 60}]}]}
    proposal = {"asset_class_targets": [target(name, share, baseline_links=[
        {"view": "holdings", "asset_class": "book", "relationship": "partial_overlap", "share_pct": share, "capital_component": True}])
        for name, share in (("part_a", 40), ("part_b", 60))],
        "current_sleeve_actions": [{"asset_class": "cash", "action": "HOLD"}]}
    ledger = funding_ledger(snapshot, proposal)
    assert ledger["status"] == "balanced"
    assert ledger["one_way_turnover_pct"] == 0
    proposal["asset_class_targets"][1]["baseline_links"][0]["share_pct"] = 100
    assert any("does not establish" in issue for issue in funding_ledger(snapshot, proposal)["issues"])


def test_material_queue_includes_both_reviewers_and_each_play_leg():
    def question(text):
        return {"question": text, "asset_classes": ["fertiliser"], "material_reason": "Changes margin case",
                "reuse_assessment": "No product-specific margin evidence", "decision_impact": "high"}
    reviews = [{"council_lane": "one", "market_questions": [question("What are producer margins?")],
        "play_assessments": [{"play_id": "p", "legs": [{"name": "uranium", "mechanism": "Supply", "unanswered_question": "What is contracted?"}]}]},
        {"council_lane": "two", "market_questions": [question("What is priced into gold miners?")]}]
    questions = research_questions({"market_questions": [question("What is duration risk?")]}, {}, reviews,
                                  {"market_questions": [question("What are producer margins?")]})
    queued = memo._trade_research_questions({"questions": questions})
    assert len(queued) == 4
    assert any(row.get("play_ids") == ["p"] for row in queued)
    assert reviews[0]["market_questions"][0].get("status") is None


def test_budget_is_explicit_not_three_questions(monkeypatch):
    monkeypatch.setenv("PORTFOLIO_FOLLOWUP_BUDGET_USD", "7.2")
    budget = FollowupBudget("ultra4x")
    assert sum(budget.reserve() for _ in range(8)) == 6


def test_saved_evidence_can_resolve_review_question_without_another_search():
    question = {"question": "What is the policy rate?", "asset_classes": ["cash"], "material_reason": "Carry",
                "reuse_assessment": "Need rate"}
    provisional = {"research_dispositions": [{"question": question["question"], "status": "answered",
                   "reason": "Recorded policy-rate observation answers this", "fact_ids": ["f1"]}]}
    queued = research_questions({"market_questions": [question]}, {}, [], provisional, {"facts": [fact()]})
    assert queued[0]["status"] == "answered"
    assert memo._trade_research_questions({"questions": queued}) == []
    assert research_questions({"market_questions": [question]}, {}, [], provisional, {"facts": []})[0]["status"] == "unanswered"


def test_runtime_and_script_share_one_pipeline_implementation():
    from scripts import portfolio_positioning_memo
    from backend.portfolio_runtime import code_manifest
    assert memo is portfolio_positioning_memo
    assert "scripts/portfolio_positioning_memo.py" in code_manifest()


@pytest.mark.parametrize("left,right", [
    ({"annualization": "quarterly SAAR"}, {"annualization": "Q4/Q4"}),
    ({"inflation_index": "PCE", "horizon_months": 12}, {"inflation_index": "CPI", "horizon_months": 60}),
    ({"price_basis": "nominal"}, {"price_basis": "real"}),
])
def test_economic_comparison_dimensions_are_not_interchangeable(left, right):
    evidence = {"facts": [fact("left", measurement=left), fact("right", measurement=right)]}
    proposal = {"financial_comparisons": [{"left_fact_id": "left", "right_fact_id": "right"}]}
    assert financial_comparison_issues(proposal, evidence)[0]["status"] == "not_comparable"
    assert linked_facts(proposal) == {"left", "right"}


def test_arithmetic_is_computed_and_missing_inputs_stay_unknown():
    upper = fact("upper")
    upper["value"] = 4.0
    proposal = {"calculations": [{"operation": "midpoint", "fact_ids": ["lower", "upper"]}]}
    lower = fact("lower", measurement={"price_basis": "nominal", "reference_period": "2026-09-18"})
    upper["measurement"] = lower["measurement"]
    result = calculate_financial_claims(proposal, {"facts": [lower, upper]})
    assert result[0]["computed_value"] == 3.875
    assert calculate_financial_claims(proposal, {"facts": []})[0]["computed_value"] is None


def test_stale_details_are_not_carried_to_changed_final_target():
    previous = target("gold", 4, rationale="Hedge", fact_ids=["f1"], investment_case={"downside": "Saved case"})
    evidence = {"facts": [fact()]}
    previous["detail_evidence_hash"] = detail_basis(previous, evidence)
    unchanged = {"asset_class_targets": [target("gold", 4, rationale="Hedge", fact_ids=["f1"])]}
    result, stale = retain_current_details(unchanged, {"asset_class_targets": [previous]}, evidence)
    assert not stale and result["asset_class_targets"][0]["investment_case"]
    unchanged["asset_class_targets"][0]["target_pct"] = 10
    result, stale = retain_current_details(unchanged, {"asset_class_targets": [previous]}, evidence)
    assert len(stale) == 1 and "investment_case" not in result["asset_class_targets"][0]
    evidence["facts"][0]["value"] = 6
    assert retain_current_details({"asset_class_targets": [previous]}, {"asset_class_targets": [previous]}, evidence)[1]


def test_patches_correct_claims_not_weights_identifiers_or_unverified_sources():
    original = {"executive_summary": "4% real yield", "asset_class_targets": [target("cash", 100)]}
    patches = [dict(path=["executive_summary"], original="4% real yield", replacement="4% nominal yield", reason="Nominal is not real", fact_ids=["f1"]),
        dict(path=["asset_class_targets", 0, "asset_class"], original="cash", replacement="gold", reason="Like it", fact_ids=[]),
        dict(path=["asset_class_targets", 0, "target_pct"], original=100, replacement=40, reason="Like it", fact_ids=[]),
        dict(path=["executive_summary"], original="4% nominal yield", replacement="Guaranteed", reason="Unknown", fact_ids=["missing"]), None]
    result = apply_claim_patches(original, {"patches": patches}, {"facts": [fact()]})
    assert result["executive_summary"] == "4% nominal yield"
    assert result["asset_class_targets"] == original["asset_class_targets"]
    assert len(result["claim_corrections"]) == 1
    assert len(result["unapplied_claim_corrections"]) == 4
    assert original["executive_summary"] == "4% real yield"


def test_failed_review_does_not_become_supporting_consensus():
    reviews = prepare_reviews([{"stage_status": "failed", "model": "ling", "error": "400"},
        {"stage_status": "complete", "model": "opus", "findings": [{"argument": "Nominal is not real", "kind": "factual_correction"}]}])
    audit = judgment_audit({}, reviews, {"facts": []})
    assert [row["contributed"] for row in audit["contributors"]] == [False, True]
    assert len(audit["unresolved_findings"]) == 1


def test_brief_passes_to_blind_allocator_without_positions_or_plays():
    context = {"mandate": {"portfolio_scope": "thematic_sleeve", "tax_cost_policy": "No forced realisations",
                          "currency_hedge_policy": "Unhedged"}, "investment_plays": [{"title": "SECRET"}], "asset_classes": [{"asset_class": "SECRET"}]}
    neutral = independent_context(context, "2026-09-18")
    prompt = allocation_prompt("blind_macro_prior", {}, neutral)
    assert "SECRET" not in json.dumps(prompt)
    assert neutral["investment_constraints"] == context["mandate"]


def test_unresearched_leg_is_not_neutral_five_and_reader_explains_partial_adoption():
    plays = [{"id": "p", "title": "Scarcity"}]
    assessments = complete_play_assessments(plays, [{"play_id": "p", "score": 5, "verdict": "watch",
        "allocation_effect": "Partly adopted: 4% bullion; retain short-duration bonds.",
        "legs": [{"name": "Fertiliser", "score": 5, "verdict": "needs_research", "unanswered_question": "What are margins?"}]}])
    assert assessments[0]["legs"][0]["score"] is None
    markdown = render_portfolio_memo(snapshot={}, structured={"play_assessments": assessments}, evidence_brief={}, citations=[])
    assert "Partly adopted: 4% bullion" in markdown
    assert "Fertiliser - Not yet assessed" in markdown
    assert "What are margins?" in markdown


def test_play_adoption_weights_come_from_final_allocation_not_narrative():
    result = play_outcomes({"asset_class_targets": [target("bullion", 4)], "play_assessments": [{
        "verdict": "watch", "selected_exposures": ["bullion", "missing"], "portfolio_action": "Partly adopted"}]})
    play = result["play_assessments"][0]
    assert play["verdict"] == "watch"
    assert play["adopted_allocations"][0]["target_pct"] == 4
    assert play["unresolved_exposure_links"] == ["missing"]


def test_hold_smaller_change_destination_have_separate_computed_turnover():
    snapshot = {"as_of": "2026-09-18", "portfolio": {"cash_pct": 50}, "asset_classes": [{"asset_class": "gold", "portfolio_pct": 50}]}
    proposal = {"asset_class_targets": [target("gold", 20), target("cash", 80)],
        "smaller_change_alternative": {"asset_class_targets": [target("gold", 45), target("cash", 55)]}}
    comparison = implementation_comparison(snapshot, proposal, {})
    assert comparison["destination"]["funding"]["one_way_turnover_pct"] == 30
    assert comparison["smaller_change"]["funding"]["one_way_turnover_pct"] == 5
    assert comparison["destination"]["scenarios"] == []


def test_frozen_repair_preserves_baselines_but_rejects_mandate_change(tmp_path):
    context = {"mandate": {"portfolio_scope": "thematic_sleeve"}, "asset_classes": []}
    artifact = {"portfolio_context": context, "independent_ideal": {"asset_class_targets": [target("cash", 100)]},
        "current_portfolio_assessment": {"asset_class_targets": [target("gold", 100)]}, "evidence_brief": {"facts": [fact()]}}
    source = tmp_path / "saved.json"
    source.write_text(json.dumps(artifact))
    repair = {**context, "repair_preserve_baselines": True}
    result = load_frozen_baselines(repair, tmp_path / "saved.checkpoint.json")
    assert result["independent_ideal"] == artifact["independent_ideal"]
    assert source.read_text() == json.dumps(artifact)
    repair["mandate"] = {"portfolio_scope": "whole_portfolio"}
    with pytest.raises(ValueError, match="brief changed"):
        load_frozen_baselines(repair, tmp_path / "saved.checkpoint.json")
