"""Research handoff and financial decision regressions, including the audited saved run."""

import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

import portfolio_positioning_memo as memo
from backend.portfolio_decisions import funding_ledger
from backend.portfolio_evidence import merge_briefs, normalize_facts
from backend.portfolio_independent import reconciliation_prompt
from backend.portfolio_judgment import action_basis_issues, consistency_inputs, materialize_retained_weights, decision_revision_scope, apply_decision_revision
from backend.portfolio_memo import play_rating
from backend.portfolio_research import matching_question, normalize_questions, restore_phase_research, refresh_signed_evidence
from backend.portfolio_retrieval import ParallelSourceProvider
from backend.portfolio_runtime import CURRENT_RUNTIME, PortfolioRuntime


def source_brief(identifier="flow", value=-95, excerpt="Inventories declined by 95 million barrels."):
    return {"facts": [{"id": identifier, "metric": "Inventory change", "value": value, "unit": "million barrels",
        "kind": "observed_macro", "benchmark": "Global oil", "currency": "not_applicable", "observed_at": "2026-08-31",
        "published_at": "2026-09-11", "vintage": "September", "source_ids": [identifier], "source_excerpt": excerpt}],
        "source_packet": {"as_of": "2026-09-19", "sources": [{"id": identifier, "url": "https://example.org/" + identifier,
            "published_at": "2026-09-11", "excerpt": excerpt}]}}


def research_question(**fields):
    return {"question": "What is the measured inventory change?", "topic": "oil", "economic_question": "inventory_change",
        "geography": "global", "period": "August 2026", "horizon": "12 months", "required_dimensions": ["inventories"],
        "asset_classes": ["energy"], "material_reason": "Tests physical scarcity", "reuse_assessment": "Use the saved inventory report",
        "answers": [{"dimension": "inventories", "status": "answered", "answer": "Stocks declined by 95 million barrels", "fact_ids": ["flow"]}], **fields}


@pytest.mark.asyncio
@pytest.mark.parametrize("record_store", [False, True])
async def test_real_checkpoint_roundtrip_restores_phase_research_not_old_decisions(tmp_path, monkeypatch, record_store):
    monkeypatch.setenv("PORTFOLIO_RESEARCH_BUDGET_USD", "0.60")
    old = PortfolioRuntime(tmp_path / "old.checkpoint.json", record_store=record_store)
    brief = source_brief()
    question = normalize_questions([research_question()], brief)[0]
    question.update(retrieval_status="succeeded", processing_status="complete")
    old.partial.update(evidence_brief=brief, macro_positioning={"secret": "Do not expose previous decisions"},
        targeted_research_results={"old_lane": {"question": question, "evidence_brief": {**brief, "question_answers": question["answers"]}}},
        research_phase_results={"plays": {"phase": "plays", "questions": [question]}})
    old.research_reservations = {"paid_task": {"estimate_usd": .6, "status": "reserved"}}
    old.save()
    resumed = PortfolioRuntime(tmp_path / "new.checkpoint.json", resume=old.checkpoint, record_store=record_store)
    assert "evidence_brief" not in resumed.partial and "macro_positioning" not in resumed.partial
    assert resumed.research_reservations == old.research_reservations
    blind, _ = restore_phase_research({}, resumed.partial, "independent")
    assert not blind.get("facts") and not blind["research_questions"]
    gather = AsyncMock(side_effect=AssertionError("Saved work must not make a new provider call"))
    monkeypatch.setattr(ParallelSourceProvider, "gather", gather)
    token = CURRENT_RUNTIME.set(resumed)
    try:
        result, searches, report = await memo._run_question_research({}, "deep", {"phase": "plays", "questions": [research_question()]})
        assert result["facts"] and result["source_packet"]["sources"]
        assert report["answered"] == 1 and not searches and gather.await_count == 0
        assert report["budget"]["reserved_estimate_usd"] == .6
        assert result["research_questions"][0]["answers"][0]["answer"]
    finally:
        CURRENT_RUNTIME.reset(token)


def test_unknown_legacy_phase_is_not_admitted_to_blind_or_current():
    saved = {"targeted_research_results": {"unknown": {"evidence_brief": source_brief()}}}
    for phase in ("independent", "current", "plays"):
        assert not restore_phase_research({}, saved, phase)[0].get("facts")
    assert restore_phase_research({}, saved, "challenge")[0]["facts"]


@pytest.mark.asyncio
async def test_resume_extracts_already_paid_sources_without_repeating_discovery(tmp_path, monkeypatch):
    monkeypatch.setenv("PORTFOLIO_RESEARCH_BUDGET_USD", "0.60")
    question = normalize_questions([research_question(answers=[])])[0]
    question.update(retrieval_status="succeeded", processing_status="failed")
    old = PortfolioRuntime(tmp_path / "old.checkpoint.json")
    old.partial.update(targeted_research_results={"independent:raw": {"phase": "independent", "question": question,
        "parallel": {"results": [{"url": "https://example.org/flow", "content": "Inventories declined by 95 million barrels."}]},
        "evidence_brief": {"facts": [], "stage_error": "Interrupted extraction"}}})
    old.research_reservations = {"paid": {"estimate_usd": .6, "status": "reserved"}}
    old.save()
    resumed = PortfolioRuntime(tmp_path / "next.checkpoint.json", resume=old.checkpoint)
    gather = AsyncMock(side_effect=AssertionError("Do not repay for saved discovery"))
    monkeypatch.setattr(ParallelSourceProvider, "gather", gather)
    async def structure(lane, **kwargs):
        assert lane["parallel"]["results"][0]["content"]
        lane["evidence_brief"] = {**source_brief(), "question_answers": research_question()["answers"]}
        return lane
    monkeypatch.setattr(memo, "_structure_evidence_lane", structure)
    token = CURRENT_RUNTIME.set(resumed)
    try:
        _, lanes, report = await memo._run_question_research({}, "deep", {"phase": "independent", "questions": [research_question(answers=[])]})
        assert report["answered"] == 1 and lanes and not gather.await_count
    finally:
        CURRENT_RUNTIME.reset(token)


def test_alias_reuse_retains_distinct_regions_periods_and_horizons():
    old = normalize_questions([research_question()])[0]
    incoming = normalize_questions([research_question(economic_question="new_key")])[0]
    assert matching_question(incoming, {old["id"]: old}) == old
    paraphrase = normalize_questions([research_question(question="How much oil left storage?", reuse_question_id=old["id"], economic_question="new_key")])[0]
    assert matching_question(paraphrase, {old["id"]: old}) == old
    for field in ("geography", "period", "horizon"):
        changed = normalize_questions([research_question(**{field: "different"}, reuse_question_id=old["id"])])[0]
        assert matching_question(changed, {old["id"]: old}) is None


@pytest.mark.parametrize("value,excerpt,source", [
    (.961, "2026-09-11: |0.9610 |", r"2026-09-11: |0\.9610 |"),
    (4.838, r"Yield: **4\.8380**", "Yield: <strong>4.8380</strong>"),
    (-.961, "Yield: -0.961", "Yield:&nbsp;-0.961"),
])
def test_source_presentation_normalizes_without_changing_raw_evidence(value, excerpt, source):
    brief = source_brief(value=value, excerpt=excerpt)
    brief["source_packet"]["sources"][0]["excerpt"] = source
    original = deepcopy(brief)
    fact = normalize_facts(brief["facts"], brief["source_packet"])[0]
    assert not fact["verification_issues"]
    assert fact["source_excerpt"] == excerpt and fact["source_text_normalization"]["raw_source_preserved"]
    assert brief == original
    brief["facts"][0]["value"] = value + 1
    assert any("numeric value" in issue for issue in normalize_facts(brief["facts"], brief["source_packet"])[0]["verification_issues"])


def test_presentation_repair_does_not_clear_a_source_mismatch_or_metadata():
    brief = source_brief(value=.961, excerpt="0.961")
    brief["source_packet"]["sources"][0]["excerpt"] = "A different observation: 0.962"
    brief["facts"][0]["verification_issues"] = ["Supporting excerpt not found in retrieved source", "Missing published_at"]
    assert refresh_signed_evidence(brief)["facts"][0]["verification_issues"] == brief["facts"][0]["verification_issues"]


def target(name, weight, **fields):
    return {"asset_class": name, "min_pct": weight, "target_pct": weight, "max_pct": weight, **fields}


def test_cash_switch_is_funded_without_claiming_currency_or_instrument_equivalence():
    snapshot = {"portfolio": {"cash_pct": .426}, "asset_classes": [{"asset_class": "energy", "portfolio_pct": 99.574}]}
    proposal = {"asset_class_targets": [target("energy", 83), target("usd_bills", 17, liquidity_class="cash_equivalent")],
        "current_sleeve_actions": [{"asset_class": "cash", "action": "EXIT", "target_pct": 0, "rationale": "Move liquidity to the proposed bills; FX treatment remains to establish"}]}
    ledger = funding_ledger(snapshot, proposal)
    assert ledger["status"] == "balanced" and ledger["cash_target_pct"] == 17
    assert ledger["specified_target_total_pct"] == 100 and ledger["one_way_turnover_pct"] == 17
    assert ledger["rows"][1]["current_pct"] == 0
    assert ledger["rows"][2]["current_pct"] == .426 and ledger["rows"][2]["target_pct"] == 0
    proposal["retain_unmentioned"] = True
    assert funding_ledger(snapshot, materialize_retained_weights(snapshot, proposal))["status"] == "balanced"
    proposal["current_sleeve_actions"] = []
    assert funding_ledger(snapshot, materialize_retained_weights(snapshot, proposal))["status"] == "unresolved"
    proposal["asset_class_targets"][1].pop("liquidity_class")
    assert funding_ledger(snapshot, proposal)["cash_target_pct"] is None, "Never guess liquidity from a bond name"


def test_research_gap_is_neither_sell_nor_forced_hold_and_risk_justification_survives():
    snapshot = {"portfolio": {"cash_pct": 0}, "asset_classes": [{"asset_class": "uranium", "portfolio_pct": 100}]}
    proposal = {"asset_class_targets": [target("cash", 100, action_basis={"category": "liquidity", "reason": "Pending review"})],
        "current_sleeve_actions": [{"asset_class": "uranium", "action": "EXIT", "action_basis": {
            "category": "research_gap", "reason": "Unresearched"}}]}
    original = deepcopy(proposal)
    assert action_basis_issues(snapshot, proposal)[0]["asset_class"] == "uranium"
    assert proposal == original
    proposal["current_sleeve_actions"][0]["action_basis"] = {"category": "risk", "reason": "Explicit single-sector limit", "evidence_status": "unassessed"}
    assert not action_basis_issues(snapshot, proposal)


def test_reviewer_receives_actual_duration_baseline_and_calculation_counts():
    ideal = {"asset_class_targets": [target("us_treasury_notes_2_5y", 10)]}
    final = {"computed_claims": [{"status": "calculated"}] * 2 + [{"status": "unresolved"}] * 8}
    result = consistency_inputs({}, ideal, {}, final)
    assert result["baseline_allocations"]["independent_ideal"][0]["target_pct"] == 10
    assert result["calculation_counts"] == {"total": 10, "calculated": 2, "unresolved": 8}
    prompt = reconciliation_prompt({}, {"research_cutoff": "2026-09-19"}, {}, {}, {}, [], [])
    assert any("Count retained cash only once" in rule for rule in prompt["rules"])
    assert any("TIPS" in rule and "rolling cash" in rule for rule in prompt["rules"])
    assert any("relative preference" in rule for rule in prompt["rules"])


def test_provisional_score_is_not_labelled_unassessed():
    assert play_rating({"score": 6, "assessment_status": "provisional"}) == "6/10 (provisional)"
    assert "6/10" in play_rating({"score": None, "reported_judgment": {"score": 6}})
    assert play_rating({"score": None}) == "Not yet assessed"


def test_audited_cash_problem_enters_scoped_repair_without_a_reviewer_request():
    path = Path("outputs/audits/portfolio-deepseek-recovery-review-20260920/latest.json")
    if not path.exists():
        pytest.skip("Local production artifact is not checked into the repository")
    artifact = json.loads(path.read_text())
    proposal, snapshot = artifact["macro_positioning"], artifact["portfolio_snapshot"]
    original = deepcopy(proposal)
    scope = decision_revision_scope(proposal, {}, snapshot)
    assert "CASH" in scope["asset_classes"] and "USDCASHANDTBILLS03M" in scope["asset_classes"]
    # An explicit analyst response changes accounting, not weights or implied instrument identity.
    cash = deepcopy(proposal["asset_class_targets"][0])
    cash["baseline_links"] = [link for link in cash["baseline_links"] if link["view"] != "holdings"]
    cash["liquidity_class"] = "cash_equivalent"
    action = {"asset_class": "cash", "action": "EXIT", "target_pct": 0,
              "rationale": "Transfer the original cash balance into the proposed liquidity sleeve; FX remains to establish"}
    alternative_cash = deepcopy(proposal["smaller_change_alternative"]["asset_class_targets"][0])
    alternative_cash["liquidity_class"] = "cash_equivalent"
    response = {"stage_status": "complete", "reason": "Count the existing cash once, as a separate explicitly funded transfer",
        "executive_summary": proposal["executive_summary"], "target_updates": [cash], "current_sleeve_actions": [action],
        "smaller_change_alternative": {"asset_class_targets": [alternative_cash], "current_sleeve_actions": [action]}}
    repaired = apply_decision_revision(proposal, response, scope, snapshot)
    ledger = funding_ledger(snapshot, repaired)
    assert ledger["status"] == "balanced" and ledger["cash_target_pct"] == 17
    assert ledger["one_way_turnover_pct"] is not None
    smaller = funding_ledger(snapshot, materialize_retained_weights(snapshot, repaired["smaller_change_alternative"]))
    assert smaller["status"] == "balanced" and abs(smaller["specified_target_total_pct"] - 100) < .05
    assert repaired["decision_reconsideration"]["status"] == "reviewed"
    assert proposal == original


def test_generated_run_label_is_readable_without_overriding_a_custom_title():
    from backend.jobs.structured import _build_portfolio_positioning_run_label
    structured = {"analysis_date": "2026-09-19"}
    assert _build_portfolio_positioning_run_label("file", structured, {"label": "portfolio recovery"}) == "Portfolio Positioning Memo (2026-09-19)"
    assert _build_portfolio_positioning_run_label("file", structured, {"label": "Scarcity thesis"}) == "Scarcity thesis (2026-09-19)"


@pytest.mark.asyncio
@pytest.mark.parametrize("record_store", [False, True])
async def test_audited_interrupted_run_restores_all_observations_without_new_retrieval(tmp_path, monkeypatch, record_store):
    path = Path("outputs/audits/portfolio-research-led-review-20260919/latest.json")
    if not path.exists():
        pytest.skip("Local production artifact is not checked into the repository")
    artifact = json.loads(path.read_text())
    old = PortfolioRuntime(tmp_path / "audited.checkpoint.json", record_store=record_store)
    old.partial = artifact
    old.research_reservations = {"inherited": {"status": "reserved", "estimate_usd": 8.4}}
    old.save()
    resumed = PortfolioRuntime(tmp_path / "resumed.checkpoint.json", resume=old.checkpoint, record_store=record_store)
    monkeypatch.setenv("PORTFOLIO_RESEARCH_BUDGET_USD", "8.40")
    gather = AsyncMock(side_effect=AssertionError("Offline audit must not make paid calls"))
    monkeypatch.setattr(ParallelSourceProvider, "gather", gather)
    baseline = merge_briefs([lane["evidence_brief"] for lane in artifact["evidence_runs"][:3]])
    token = CURRENT_RUNTIME.set(resumed)
    try:
        evidence = baseline
        for phase in ("independent", "current", "plays"):
            evidence, _, _ = await memo._run_question_research(evidence, "deep", {
                **artifact["research_phase_results"][phase], "phase": phase})
            if phase == "independent":
                oil = {fact["id"] for key, lane in artifact["targeted_research_results"].items()
                       if "ebe340e5" in key for fact in lane["evidence_brief"]["facts"]}
                available = {fact["id"] for fact in evidence["facts"]} | set(evidence.get("fact_aliases", {}))
                assert len(oil) == 33 and oil <= available
                fertiliser = {fact["id"] for k, lane in artifact["targeted_research_results"].items()
                    if "3552ceaf" in k for fact in lane["evidence_brief"]["facts"]}
                assert not fertiliser.intersection(fact["id"] for fact in evidence["facts"])
        restored = {row["id"] for row in evidence["facts"]} | set(evidence.get("fact_aliases", {}))
        expected = {row["id"] for row in artifact["evidence_brief"]["facts"]}
        assert expected <= restored
        assert len(expected) == 477 and not gather.await_count
    finally:
        CURRENT_RUNTIME.reset(token)
