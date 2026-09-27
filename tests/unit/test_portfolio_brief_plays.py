from copy import deepcopy
import json

from backend.portfolio_independent import (
    complete_play_assessments, independent_context, normalize_plays,
    reconciliation_prompt, validate_independent_stage,
)
from backend.portfolio_judgment import play_outcomes, research_questions
from backend.portfolio_memo import render_portfolio_memo
from backend.portfolio_recovery import recover_optional_fields
from backend.portfolio_runtime import PortfolioRuntime
from backend.portfolio_tasks import decision_source_check_plan


def plays():
    return normalize_plays([{"title": "Mining services", "thesis": "Mining activity may support equipment and service demand."}])


def test_brief_assessment_retains_score_without_requiring_components():
    ideas = plays()
    raw = [{"play_id": ideas[0]["id"], "score": 6, "verdict": "watch", "reason": "Demand is plausible; pricing is uncertain.",
            "portfolio_action": "No new allocation.", "legs": [{"unanswered_question": "Launch more research"}]}]
    before = deepcopy(raw)
    result = complete_play_assessments(ideas, raw, brief=True)
    assert result[0]["score"] == 6 and result[0]["verdict"] == "watch"
    assert result[0]["assessment_mode"] == "brief"
    assert "legs" not in result[0] and "coverage_status" not in result[0]
    assert complete_play_assessments(ideas, result) == result
    assert raw == before


def test_brief_schema_and_optional_field_recovery_keep_the_portfolio():
    ideas = plays()
    prompt = reconciliation_prompt({"facts": []}, independent_context({}, "2026-09-23"), {}, {}, {}, ideas, [], brief_plays=True)
    assert "legs" not in prompt["required_schema"]["play_assessments"][0]
    assert "Do not decompose" in " ".join(prompt["rules"])
    assert "Assess every leg" not in " ".join(prompt["rules"])
    output = {"executive_summary": "The core analysis remains useful.",
              "asset_class_targets": [{"asset_class": "cash", "min_pct": 100, "target_pct": 100, "max_pct": 100}]}
    recovered, warnings = recover_optional_fields(output, prompt)
    assert recovered["asset_class_targets"][0]["target_pct"] == 100
    assert recovered["play_assessments"][0]["score"] is None
    assert recovered["play_assessments"][0]["assessment_mode"] == "brief"
    assert not validate_independent_stage(recovered, prompt)
    assert warnings


def test_new_ideas_are_assessed_even_when_final_weights_do_not_change():
    neutral = independent_context({}, "2026-09-23")
    provisional_prompt = reconciliation_prompt({}, neutral, {}, {}, {}, [], [], brief_plays=True)
    assert "play_assessments" not in provisional_prompt["required_schema"]
    ideas = normalize_plays([{"title": title, "thesis": "Test the investment case."} for title in (
        "Fertiliser", "Precious metals miners", "Oil producers", "Uranium", "Mining services", "Physical gold")])
    final_prompt = reconciliation_prompt({}, neutral, {}, {}, {}, ideas, [], provisional={}, brief_plays=True)
    assert "play_assessments" in final_prompt["required_schema"]["updates"]
    assert "still return the newly introduced play assessments" in " ".join(final_prompt["rules"])
    rows = complete_play_assessments(ideas, [], brief=True)
    assert len(rows) == 6
    assert all(row["score"] is None and row["assessment_mode"] == "brief" and "legs" not in row for row in rows)


def test_brief_ideas_do_not_create_followups_or_source_check_obligations():
    question = {"question": "Order books?", "play_ids": [plays()[0]["id"]]}
    core_question = {"question": "Does the portfolio's duration fit its horizon?"}
    proposal = {"market_questions": [question, core_question], "play_assessments": [
        {"play_id": plays()[0]["id"], "assessment_mode": "brief", "fact_ids": ["idea_only"],
         "legs": [{"unanswered_question": "Unexpected component question"}]}],
        "asset_class_targets": [{"asset_class": "bonds", "target_pct": 100, "fact_ids": ["decision"]}]}
    assert [q["question"] for q in research_questions({}, {}, [], proposal, include_play_questions=False)] == [core_question["question"]]
    facts = {"facts": [{"id": "idea_only"}, {"id": "decision"}]}
    assert decision_source_check_plan(facts, proposal)["fact_ids"] == ["decision"]
    proposal["asset_class_targets"][0]["fact_ids"].append("idea_only")
    assert set(decision_source_check_plan(facts, proposal)["fact_ids"]) == {"decision", "idea_only"}


def test_brief_play_is_short_appendix_without_leg_expansion_or_process_text():
    ideas = plays()
    rows = complete_play_assessments(ideas, [{"play_id": ideas[0]["id"], "score": 6, "verdict": "watch",
        "reason": "Demand is plausible; pricing remains uncertain.", "portfolio_action": "No addition.",
        "selected_exposures": []}], brief=True)
    structured = {"workflow_version": 4, "executive_summary": "Core judgment first.", "play_assessments": rows,
                  "implementation_notes": ["Implement the core portfolio deliberately."]}
    markdown = render_portfolio_memo(snapshot={}, structured=structured, evidence_brief={}, citations=[])
    assert markdown.index("## Implementation And Alternatives") < markdown.index("## Investment Plays") < markdown.index("## Supporting Research")
    play_text = markdown.split("## Investment Plays")[1].split("## Supporting Research")[0]
    assert "6/10" in play_text and "Watch" in play_text
    assert "No addition." in play_text and "Demand is plausible" in play_text
    assert "component-by-component" not in play_text and len(play_text.split()) < 45


def test_brief_play_adoption_uses_actual_funded_targets():
    proposal = {"asset_class_targets": [{"asset_class": "services", "display_name": "Mining services", "target_pct": 3}],
        "play_assessments": complete_play_assessments(plays(), [{"play_id": plays()[0]["id"], "score": 7,
            "verdict": "include", "reason": "Existing research supports the case.", "portfolio_action": "Add 3% funded from cash.",
            "selected_exposures": ["services"]}], brief=True)}
    result = play_outcomes(proposal)["play_assessments"][0]
    assert result["adopted_allocations"][0]["target_pct"] == 3
    assert result["allocation_effect"] == "Add 3% funded from cash."


def test_new_runs_default_to_brief_but_old_checkpoints_keep_their_contract(tmp_path):
    assert PortfolioRuntime().partial["play_assessment_mode"] == "brief"
    old = tmp_path / "old.checkpoint.json"
    old.write_text(json.dumps({"workflow_version": 4, "partial_artifact": {}}))
    assert PortfolioRuntime(resume=old).partial["play_assessment_mode"] == "components"
    old.write_text(json.dumps({"workflow_version": 4, "partial_artifact": {"play_assessment_mode": "brief"}}))
    assert PortfolioRuntime(resume=old).partial["play_assessment_mode"] == "brief"


def test_brief_plays_do_not_add_funding_calls():
    from backend.portfolio_funding import estimate_plan
    with_ideas = {"investment_plays": plays()}
    assert estimate_plan({}, {}) == estimate_plan(with_ideas, {})
    resumed = {"workflow_version": 4, "play_assessment_mode": "brief"}
    assert estimate_plan({}, {}, resumed) == estimate_plan(with_ideas, {}, resumed)
    old = {"workflow_version": 4}
    assert sum(estimate_plan(with_ideas, {}, old).values()) == sum(estimate_plan({}, {}, old).values()) + 1
