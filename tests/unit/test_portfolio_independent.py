import argparse
import asyncio
from copy import deepcopy
import json
from unittest.mock import AsyncMock

import pytest

import portfolio_positioning_memo as memo
from backend.portfolio_decisions import analysis_health, build_decision, funding_ledger, recorded_display_rows
from backend.portfolio_independent import (
    allocation_prompt, complete_play_assessments, independent_context, normalize_plays,
    proposal_reference_errors, reconciliation_prompt, review_prompt, validate_independent_stage,
)
from backend.portfolio_memo import render_portfolio_memo
from backend.portfolio_recovery import recover_optional_fields
from backend.portfolio_runtime import CURRENT_RUNTIME, PortfolioRuntime, digest


CUTOFF = "2026-09-17T04:47:31Z"


def snapshot():
    return {"as_of": CUTOFF, "portfolio": {"total_value": 100000, "cash_pct": 62.42},
            "asset_classes": [{"asset_class": "ENERGY", "display_name": "Energy", "portfolio_pct": 37.58},
                              {"asset_class": "CASH", "display_name": "Cash", "portfolio_pct": 62.42}]}


def target(asset, weight, **extra):
    return {"asset_class": asset, "display_name": asset.title(), "min_pct": max(0, weight - 5),
            "target_pct": weight, "max_pct": min(100, weight + 7), "thesis_conviction": "STRONG",
            "rationale": "Supported investment argument", "fact_ids": ["f1"], "contrary_evidence": ["A reversal is possible"], **extra}


def evidence():
    return {"executive_summary": "A conditional macro view", "evidence_status": "complete",
            "facts": [{"id": "f1", "kind": "market_price", "metric": "yield", "value": 4,
                       "benchmark": "Bills", "source_ids": ["s1"]}],
            "source_packet": {"as_of": CUTOFF, "sources": [{"id": "s1", "url": "https://example.org/rates", "title": "Rates", "excerpt": "Yield 4%"}]},
            "macro_scorecard": {"policy_rates": "Restrictive"}, "market_view": {"key_messages": ["Compare carry and downside"]},
            "commodity_prices": [{"commodity": "Fertiliser", "price_context": "Conditional evidence", "fact_ids": ["f1"]}],
            "broker_themes": [{"theme": "Supply risks", "fact_ids": ["f1"]}]}


def empty_shape(schema):
    if isinstance(schema, dict):
        return {key: empty_shape(value) for key, value in schema.items()}
    return [] if isinstance(schema, list) else None


def test_independent_requests_do_not_change_with_holdings_catalogue_or_plays():
    a = snapshot()
    a.update(available_asset_classes=[{"asset_class": "OWNED_ONLY"}], investment_plays=[{"title": "Own idea", "thesis": "Buy my idea"}],
             macro_prior={"asset_class_targets": [target("LEAK", 100)]}, frozen_research_query="Our portfolio-specific question")
    b = {**a, "asset_classes": [{"asset_class": f"DIFFERENT_{i}", "portfolio_pct": 5} for i in range(20)],
         "available_asset_classes": [{"asset_class": "DIFFERENT_ONLY"}], "investment_plays": []}
    context = independent_context(a, CUTOFF)
    assert context == independent_context(b, CUTOFF)
    first = allocation_prompt("blind_macro_prior", evidence(), context)
    second = allocation_prompt("blind_macro_prior", evidence(), independent_context(b, CUTOFF))
    assert digest(first) == digest(second)
    assert all(term not in json.dumps(first) for term in ("OWNED_ONLY", "LEAK", "Own idea", "37.58", "100000"))
    assert "portfolio_context" not in first and "current_portfolio" not in first
    assert independent_context({"mandate": {"base_currency": "AUD"}}, CUTOFF) != context


def test_current_assessor_is_not_given_ideal_or_plays():
    prompt = allocation_prompt("portfolio_aware_allocator", evidence(), independent_context({}, CUTOFF), snapshot())
    assert "independent_ideal" not in prompt and "investment_plays" not in prompt
    assert prompt["current_portfolio"]["current_asset_classes"][0]["current_pct"] == 37.58


@pytest.mark.parametrize("risk", ["low", "medium", "high"])
@pytest.mark.parametrize("horizon", ["1-2 years", "3-5 years", "5+ years"])
def test_simple_profile_reaches_independent_and_current_views_without_anchoring(risk, horizon):
    context = {**snapshot(), "mandate": {"risk_tolerance": risk, "time_horizon": horizon},
               "investment_plays": [{"title": "Hidden play", "thesis": "Hidden premise"}]}
    before = deepcopy(context)
    neutral = independent_context(context, CUTOFF)
    assert neutral["investment_constraints"] == context["mandate"]
    compact = memo._compact_snapshot(context)
    assert compact["mandate"] == context["mandate"]
    ideal = allocation_prompt("blind_macro_prior", evidence(), neutral)
    current = allocation_prompt("portfolio_aware_allocator", evidence(), neutral, compact)
    assert "current_portfolio" not in ideal and "Hidden play" not in json.dumps(ideal)
    assert current["current_portfolio"]["mandate"] == context["mandate"]
    assert "investment_plays" not in current
    assert digest(ideal) != digest(allocation_prompt("blind_macro_prior", evidence(), independent_context({}, CUTOFF)))
    assert "max_drawdown_pct" not in neutral["investment_constraints"]
    assert "horizon_months" not in neutral["investment_constraints"]
    assert context == before


@pytest.mark.parametrize("band,ceiling", [("1-2 years", 24), ("3-5 years", 60), ("5+ years", None)])
def test_horizon_band_counts_as_supplied_without_becoming_an_exact_deadline(band, ceiling):
    from backend.portfolio_decisions import mandate_horizon_ceiling, mandate_issues
    mandate = {"time_horizon": band, "risk_tolerance": "high"}
    assert mandate_horizon_ceiling(mandate) == ceiling
    assert "Missing horizon months" not in mandate_issues(mandate)
    proposed = {"asset_class_targets": [target("ENERGY", 35, investment_case={"horizon_months": 120}), target("CASH", 65)]}
    decision = build_decision({**snapshot(), "mandate": mandate}, proposed, evidence())
    assert "horizon_months" not in decision["missing_mandate"]
    energy = next(row for row in decision["funding"]["rows"] if row["asset_class"] == "ENERGY")
    assert ("Investment holding period exceeds the portfolio mandate" in energy["open_questions"]) == (ceiling is not None)
    assert energy["thesis_conviction"] == "STRONG"
    assert decision["mandate"] == mandate


def test_invalid_optional_profile_is_reported_without_discarding_the_proposal():
    from backend.portfolio_decisions import mandate_issues
    mandate = {"risk_tolerance": {"bad": True}, "time_horizon": ["5+ years"]}
    assert "Invalid risk tolerance" in mandate_issues(mandate)
    assert "Invalid time horizon" in mandate_issues(mandate)
    decision = build_decision({**snapshot(), "mandate": mandate},
                              {"asset_class_targets": [target("ENERGY", 35), target("CASH", 65)]}, evidence())
    assert len(decision["funding"]["rows"]) == 2


def test_missing_mandate_keeps_thesis_conviction_and_range_hold():
    decision = build_decision(snapshot(), {"asset_class_targets": [target("ENERGY", 35), target("CASH", 65)]}, evidence())
    energy = decision["funding"]["rows"][0]
    assert energy["thesis_conviction"] == "STRONG"
    assert energy["sizing_confidence"] == "UNASSESSED"
    assert energy["action"] == "HOLD" and energy["reference_trade_action"] == "TRIM"
    assert decision["status"] == "needs_review"


def test_historical_display_preserves_recorded_ratings_and_provenance_is_separate():
    artifact = {"portfolio_snapshot": snapshot(), "structured_data": {"asset_class_targets": [target("ENERGY", 35, conviction="MEDIUM")]}}
    before = deepcopy(artifact)
    assert analysis_health(artifact)["status"] == "historical"
    assert recorded_display_rows(artifact)[0]["model_thesis_conviction"] == "STRONG"
    assert artifact == before


def test_plays_have_stable_identity_without_silent_truncation():
    plays = normalize_plays([{"title": f"Play {i}", "thesis": "Hypothesis"} for i in range(30)])
    assert len(plays) == 30
    assert normalize_plays(plays) == plays
    assessments = complete_play_assessments(plays, [{"play_id": plays[0]["id"], "score": 8, "verdict": "watch", "reason": "Already represented"}])
    assert len(assessments) == 30 and assessments[0]["reported_judgment"]["score"] == 8
    assert assessments[0]["coverage_status"] == "incomplete" and assessments[1]["score"] is None
    with pytest.raises(ValueError):
        normalize_plays([{"title": "Missing thesis"}])


def test_missing_play_fields_do_not_reject_an_allocation():
    plays = normalize_plays([{"title": "Fertiliser", "thesis": "Conditional supply opportunity"}])
    prompt = reconciliation_prompt(evidence(), independent_context({}, CUTOFF), {}, {}, snapshot(), plays, [])
    output = {"asset_class_targets": [target("ENERGY", 35), target("CASH", 65)], "executive_summary": "A useful proposal"}
    normalized, warnings = recover_optional_fields(output, prompt)
    assert not validate_independent_stage(normalized, prompt)
    assert normalized["play_assessments"][0]["score"] is None
    assert normalized["asset_class_targets"] == recover_optional_fields(output, prompt)[0]["asset_class_targets"]
    assert warnings


def test_synthesis_reference_check_catches_zero_instead_of_five():
    ideal = {"asset_class_targets": [target("ENERGYCOMMODITIES", 5), target("CASH", 95)]}
    proposal = {"reconciliation": [{"asset_class": "ENERGYCOMMODITIES", "ideal_reference_pct": 0, "current_reference_pct": None}]}
    assert "must be 5" in proposal_reference_errors(proposal, ideal, {})[0]
    proposal["reconciliation"][0]["ideal_reference_pct"] = 5
    assert not proposal_reference_errors(proposal, ideal, {})


def test_memo_preserves_both_views_comments_triggers_and_new_exposures():
    ideal = {"executive_summary": "Unanchored ideal", "asset_class_targets": [target("FERTILISER_PRODUCERS", 15), target("CASH", 85)],
             "excluded_opportunities": [{"exposure": "Long duration", "reason": "The price is not attractive"}]}
    structured = {"executive_summary": "Final market judgment", "independent_ideal": ideal,
        "current_portfolio_assessment": {"executive_summary": "Current book assessment", "current_assessment": [{"asset_class": "ENERGY", "action": "HOLD", "rationale": "Range remains suitable"}]},
        "asset_class_targets": [target("FERTILISER_PRODUCERS", 5), target("CASH", 95)],
        "allocator_commentary": {"comparison_summary": "The alternative is better only at the right price",
            "portfolio_level_comments": ["Retain flexibility"], "asset_class_comments": [{"asset_class": "CASH", "commentary": "No forced trade"}]},
        "implementation_notes": ["Check transaction costs"], "monitoring_triggers": ["Supply normalisation"],
        "risk_flags": ["Demand can weaken"], "decision": {"research_priorities": [{"question": "DIAGNOSTIC_ONLY"}]}}
    markdown = render_portfolio_memo(snapshot=snapshot(), structured=structured, evidence_brief=evidence(), citations=[])
    for content in ("Independent Ideal Portfolio", "Current book assessment", "Fertiliser Producers", "No forced trade",
                    "Check transaction costs", "Supply normalisation", "Demand can weaken", "Opportunities Not Selected"):
        assert content.casefold() in markdown.casefold()
    assert "DIAGNOSTIC_ONLY" not in markdown and "fact_ids" not in markdown
    assert "## Investment Plays" not in markdown


@pytest.mark.asyncio
@pytest.mark.parametrize("play_mode", ["brief", "components"])
@pytest.mark.parametrize("reconsider", [False, True])
@pytest.mark.parametrize("large_evidence", [False, True])
async def test_full_independent_workflow_and_checkpoint_reuse(tmp_path, monkeypatch, reconsider, large_evidence, play_mode):
    context = snapshot()
    context["investment_plays"] = [{"title": "Fertiliser", "thesis": "Test a supply constraint"}]
    context["available_asset_classes"] = [{"asset_class": "OWNED_ONLY"}]
    path = tmp_path / "context.json"
    path.write_text(json.dumps(context))
    output = tmp_path / "memo.json"
    args = argparse.Namespace(portfolio_context_file=str(path), dump_json=str(output), query="OWNED_ONLY investor question", mode="deep", run_label="Test", resume_checkpoint=None)
    monkeypatch.setattr(memo, "FundingGuard", lambda: None)
    research_evidence = evidence()
    research_evidence["facts"] += [{"id": identifier, "kind": "forecast", "metric": "Net margin", "benchmark": "Fertiliser producers", "interpretation": metric,
        "value": value, "unit": "percent", "target_period": "2027", "comparison_groups": ["fertiliser-margin"],
        "source_ids": ["s1"], "source_excerpt": "Opposing margin estimates"}
        for identifier, metric, value in [("late-support", "Margin recovery", 20), ("late-opposition", "Margin squeeze", 5)]]
    if large_evidence:
        research_evidence["facts"] += [{"id": f"large_{i}", "metric": f"Distinct measure {i}", "value": i,
            "unit": "index", "benchmark": f"Market {i}", "observed_at": CUTOFF, "source_ids": ["s1"],
            "source_excerpt": f"Observation {i}: " + "A separate dated market observation. " * 90} for i in range(350)]
        research_evidence["research_questions"] = [{"id": f"question_{i}", "question": f"What changed in market {i}?",
            "required_dimensions": ["change"], "status": "answered",
            "asset_classes": [f"MARKET_{i}"], "answers": [{"dimension": "change", "status": "answered",
                "answer": "Dated observation retained", "fact_ids": [f"large_{i}"]}]} for i in range(75)]
    research = AsyncMock(return_value=(research_evidence, [], []))
    monkeypatch.setattr(memo, "_run_evidence_ensemble", research)
    source_checks = AsyncMock(return_value=research_evidence)
    monkeypatch.setattr(memo, "_run_evidence_reconciliation", source_checks)
    monkeypatch.setattr(memo, "_run_targeted_research", AsyncMock(return_value=(research_evidence, [], {"status": "not_needed"})))
    calls = []
    current_dispatched = asyncio.Event()

    async def client(model, messages, **kwargs):
        assert "max_tokens" not in kwargs
        prompt = json.loads(messages[0]["content"])
        calls.append(prompt)
        result = empty_shape(prompt["required_schema"])
        task = prompt["task"]
        if "asset_class_targets" in result:
            result["executive_summary"] = "Analytical judgment"
            if "independent ideal" in task:
                await asyncio.wait_for(current_dispatched.wait(), timeout=10)
                assert "OWNED_ONLY" not in json.dumps(prompt) and "investment_plays" not in prompt
                result["asset_class_targets"] = [target("FERTILISER_PRODUCERS", 15), target("CASH", 85)]
            elif "current portfolio independently" in task:
                assert "independent_ideal" not in prompt and "investment_plays" not in prompt
                current_dispatched.set()
                result["asset_class_targets"] = [target("ENERGY", 35), target("CASH", 65)]
                result["current_assessment"] = [{"asset_class": row["asset_class"], "action": "HOLD", "rationale": "Acceptable exposure"} for row in context["asset_classes"]]
            else:
                final = "after investment-case" in task
                result["asset_class_targets"] = [target("FERTILISER_PRODUCERS", 5 if final else 20), target("ENERGY", 35), target("CASH", 60 if final else 45)]
                if final:
                    assert prompt["investment_details"]["asset_class_targets"][0]["investment_case"]["downside"] == "Input costs weaken the case"
                    assert "implementation_comparison" in prompt["computed_decision_checks"]
        elif "target_updates" in result:
            if prompt.get("update_contract") == "portfolio-final-delta-v1":
                assert "investment_case" in prompt["required_schema"]["target_updates"][0]
                assert "implementation_comparison" in prompt["computed_decision_checks"]
                result.update(reason="Investment cases favour a smaller position",
                              target_updates=[{**target("FERTILISER_PRODUCERS", 5), "fact_ids": ["late-support"],
                                  "investment_case": {"downside": "Input costs weaken the case"}}, target("CASH", 60)], updates={})
                if prompt.get("play_assessment_mode") == "brief":
                    result["updates"]["play_assessments"] = [{"play_id": play["id"], "score": 6, "verdict": "watch", "reason": "Input costs matter"}
                                                             for play in prompt.get("investment_plays", [])]
                return {"content": json.dumps(result), "finish_reason": "stop"}
            assert reconsider
            assert set(prompt["scope"]["asset_classes"]) == {"FERTILISERPRODUCERS", "CASH"}
            result.update(reason="Margin evidence warrants a smaller position", executive_summary="Reduce fertiliser to 3%; retain the balance in cash",
                target_updates=[target("FERTILISER_PRODUCERS", 3,
                    investment_case={"downside": "Margin pressure justifies the smaller position"}), target("CASH", 62)])
        elif "allocation_details" in result:
            result["allocation_details"] = [{"asset_class": row["asset_class"], "implementation": {}, "market_pricing": {},
                "investment_case": {"downside": "Input costs weaken the case"}, "alternatives": []} for row in prompt["assigned_allocations"]]
        elif "comparison_summary" in result:
            result.update(comparison_summary="Retain the independent view while adjusting for the weaker investment case",
                          portfolio_level_comments=["No need to mirror current categories"], asset_class_comments=[])
        else:
            result["summary"] = "Review the two distinct approaches"
            if reconsider and "decision_revisions" in result:
                result["decision_revisions"] = [{"asset_classes": ["FERTILISER_PRODUCERS"],
                    "funding_asset_classes": ["CASH"], "reason": "Corrected margins undermine the sizing case", "fact_ids": ["f1"]}]
        if "play_assessments" in result:
            result["play_assessments"] = [{"play_id": play["id"], "score": 6, "verdict": "watch", "reason": "Input costs matter"} for play in prompt.get("investment_plays", [])]
        return {"content": json.dumps(result), "finish_reason": "stop"}

    monkeypatch.setattr(memo, "query_model", client)
    runtime = PortfolioRuntime(output.with_suffix(".checkpoint.json"), artifact_path=output)
    runtime.partial["play_assessment_mode"] = play_mode
    token = CURRENT_RUNTIME.set(runtime)
    try:
        artifact = await memo._run_pipeline(args)
    finally:
        CURRENT_RUNTIME.reset(token)
    assert artifact["workflow_version"] == 4
    assert artifact["independent_ideal"]["asset_class_targets"][0]["target_pct"] == 15
    assert artifact["macro_positioning"]["asset_class_targets"][0]["target_pct"] == (3 if reconsider else 5)
    if reconsider:
        assert artifact["macro_positioning"]["decision_reconsideration"]["changed"]
        assert artifact["macro_positioning"]["asset_class_targets"][1]["target_pct"] == 35
        assert len([p for p in calls if p["task"] == "Reconsider only the affected investment decisions after factual correction"]) == 1
        assert calls[-1]["task"] == "Write financial commentary explaining the ideal, current portfolio and chosen changes"
    assert len([p for p in calls if "comparison_summary" in p["required_schema"]]) == 1
    assert not any("allocation_details" in p["required_schema"] for p in calls)
    assert artifact["macro_positioning"]["asset_class_targets"][0]["investment_case"]["downside"]
    assert artifact["analysis_health"]["status"] == "complete"
    assert any({"late-support", "late-opposition"} <= set(call.kwargs["review_fact_ids"])
               for call in source_checks.call_args_list[1:]), "A final citation must bring its opposing dependency into checking"
    assert all(row["payload_accounting"]["message_bytes"] > 0 for row in runtime.receipts if not row.get("reused"))
    if large_evidence:
        assert len(artifact["evidence_brief"]["facts"]) == len(research_evidence["facts"])
        if reconsider:
            correction = next(p for p in calls if p["task"] == "Reconsider only the affected investment decisions after factual correction")
            assert sum(row["target_pct"] for row in correction["proposal"]["portfolio_weights"]) == 100
            assert all(not row["id"].startswith("large_") for row in correction["evidence_brief"]["facts"])
    assert artifact["structured_data"]["asset_class_targets"][0]["conviction"] == "STRONG"
    assert "OWNED_ONLY" not in research.call_args.kwargs["query"]
    assert research.call_args.kwargs["asset_class_vocabulary"] == []
    assert "Independent Ideal Portfolio" in artifact["analyst_memo_markdown"]
    assert len([p for p in calls if "independent ideal" in p["task"]]) == 1
    tasks = [p["task"] for p in calls]
    for phase, allocator_task in (("independent", "independent ideal"), ("current", "current portfolio independently")):
        assert tasks.index("Plan decisive market research before investment judgments: " + phase) < next(
            index for index, task in enumerate(tasks) if allocator_task in task)
    if play_mode == "brief":
        assert "Plan decisive market research before investment judgments: plays" not in tasks
        assert not any("inventory of submitted investment plays" in task for task in tasks)
        first_play_assessment = next(index for index, prompt in enumerate(calls) if prompt.get("investment_plays"))
        assert calls[first_play_assessment]["task"] == "Reconcile the final portfolio after investment-case review"
        assert not artifact["provisional_recommendation"]["play_assessments"]
        assert all(not prompt.get("investment_plays") for prompt in calls if prompt.get("review_scope"))
        assert all(not case.startswith("play.") for prompt in calls for case in (prompt.get("review_scope") or {}).get("case_ids", []))
        assert artifact["work_plan"]["nodes"]["plays"]["request_count"] == 0
        assert artifact["macro_positioning"]["play_assessments"][0]["score"] == 6
        assert "legs" not in artifact["macro_positioning"]["play_assessments"][0]
    else:
        first_play_assessment = next(index for index, prompt in enumerate(calls) if "play_assessments" in prompt["required_schema"])
        play_plan_index = tasks.index("Plan decisive market research before investment judgments: plays")
        assert play_plan_index < first_play_assessment

    restored = PortfolioRuntime(tmp_path / "resumed.checkpoint.json", output.with_suffix(".checkpoint.json"))
    assert restored.workflow_version == 4
    assert restored.partial["play_assessment_mode"] == play_mode
    token = CURRENT_RUNTIME.set(restored)
    monkeypatch.setattr(memo, "query_model", AsyncMock(side_effect=AssertionError("Completed calls should be reused")))
    try:
        replay = await memo._run_pipeline(args)
    finally:
        CURRENT_RUNTIME.reset(token)
    assert replay["independent_ideal"]["output_hash"] == artifact["independent_ideal"]["output_hash"]
    assert all(row.get("reused") for row in restored.receipts)

    context["investment_plays"] = [{"title": "Different idea", "thesis": "A separate hypothesis"}]
    if play_mode == "brief":
        context["investment_plays"] += [{"title": f"Additional idea {index}", "thesis": "A separate hypothesis"} for index in range(5)]
    path.write_text(json.dumps(context))
    changed = PortfolioRuntime(tmp_path / "changed.checkpoint.json", output.with_suffix(".checkpoint.json"))
    calls.clear()
    monkeypatch.setattr(memo, "query_model", client)
    token = CURRENT_RUNTIME.set(changed)
    try:
        reconsidered = await memo._run_pipeline(args)
    finally:
        CURRENT_RUNTIME.reset(token)
    assert reconsidered["independent_ideal"]["output_hash"] == artifact["independent_ideal"]["output_hash"]
    assert reconsidered["current_portfolio_assessment"]["output_hash"] == artifact["current_portfolio_assessment"]["output_hash"]
    assert not any("independent ideal" in call["task"] or "current portfolio independently" in call["task"] for call in calls)
    assert reconsidered["play_assessments"][0]["title"] == "Different idea"
    if play_mode == "brief":
        assert len(reconsidered["play_assessments"]) == 6
        assert calls[0]["task"] == "Reconcile the final portfolio after investment-case review"
        assert not any(prompt.get("review_scope") or prompt["task"].startswith("Plan decisive market research") for prompt in calls)

    # An explicit repair keeps the two original outputs even after prompts change.
    original = json.loads(output.read_text())
    assert original["independent_ideal"]["asset_class_targets"]
    original_context = original["portfolio_context"]
    original_context["repair_preserve_baselines"] = True
    path.write_text(json.dumps(original_context))
    args.resume_checkpoint = str(output.with_suffix(".checkpoint.json"))
    args.dump_json = str(tmp_path / "repaired.json")
    repair_runtime = PortfolioRuntime(tmp_path / "repaired.checkpoint.json", output.with_suffix(".checkpoint.json"))
    monkeypatch.setattr(memo, "_run_evidence_ensemble", AsyncMock(side_effect=AssertionError("Do not repeat source discovery")))
    calls.clear()
    token = CURRENT_RUNTIME.set(repair_runtime)
    try:
        repaired = await memo._run_pipeline(args)
    finally:
        CURRENT_RUNTIME.reset(token)
    assert repaired["independent_ideal"] == original["independent_ideal"]
    assert repaired["current_portfolio_assessment"] == original["current_portfolio_assessment"]
    assert repaired["provenance"]["baseline_repair"]["source_run_id"] == output.name
    assert not any("independent ideal" in call["task"] or "current portfolio independently" in call["task"] for call in calls)


@pytest.mark.asyncio
@pytest.mark.parametrize("requested", [9000, 48000])
async def test_allocation_stage_ignores_legacy_output_caps(monkeypatch, requested):
    runtime = PortfolioRuntime()
    runtime.query = AsyncMock(return_value={"content": "{}", "stage_status": "complete"})
    prompt = {"task": "Allocate portfolio", "required_schema": {"asset_class_targets": [{"asset_class": "string"}]}}
    token = CURRENT_RUNTIME.set(runtime)
    try:
        await memo._query_stage("test/model", [{"role": "user", "content": json.dumps(prompt)}], max_tokens=requested)
    finally:
        CURRENT_RUNTIME.reset(token)
    assert "max_tokens" not in runtime.query.call_args.kwargs


@pytest.mark.asyncio
async def test_evidence_consolidation_has_no_output_cap(monkeypatch):
    query = AsyncMock(return_value={"content": '{"executive_summary":"Reconciled evidence"}', "stage_status": "complete"})
    monkeypatch.setattr(memo, "_query_stage", query)
    token = CURRENT_RUNTIME.set(PortfolioRuntime())
    try:
        result = await memo._run_evidence_reconciliation(query="neutral", mode="deep", evidence_briefs=[evidence()], asset_class_vocabulary=[])
    finally:
        CURRENT_RUNTIME.reset(token)
    query.assert_awaited_once()
    assert "max_tokens" not in query.call_args.kwargs
    assert result["executive_summary"] == "Reconciled evidence"


@pytest.mark.asyncio
async def test_selected_fact_reviews_keep_ids_all_evidence_and_prior_reviews(tmp_path, monkeypatch):
    from backend.portfolio_evidence import FACT_FIELDS, apply_fact_checks
    packet = {"as_of": CUTOFF, "sources": [{"id": "s1", "excerpt": "GDP growth 3.1 percent", "published_at": "2026-09-15"}]}
    fact = {"id": "f1", "kind": "observed_macro", "metric": "GDP growth", "value": 3.1, "unit": "percent",
            "currency": "not_applicable", "benchmark": "GDP", "observed_at": "2026-09-15", "published_at": "2026-09-15",
            "vintage": "first", "source_ids": ["s1"], "source_excerpt": "GDP growth 3.1 percent"}
    facts = [{**deepcopy(fact), "id": f"f{i}"} for i in range(40)]
    for row in facts:
        row.pop("claim_review", None)
    brief = {**evidence(), "source_packet": packet, "facts": facts}
    runtime = PortfolioRuntime(tmp_path / "review.checkpoint.json")
    calls = []

    async def query(model, messages, **kwargs):
        prompt = json.loads(messages[0]["content"])
        calls.append(prompt)
        return {"content": json.dumps({"fact_checks": [{"fact_id": row["id"], "checks": {key: "supported" for key in FACT_FIELDS},
            "reason": "Exact source checked"} for row in prompt["evidence"]["facts"]]})}
    monkeypatch.setattr(memo, "query_model", query)
    token = CURRENT_RUNTIME.set(runtime)
    try:
        result = await memo._run_evidence_reconciliation(query="neutral", mode="deep", evidence_briefs=[brief], asset_class_vocabulary=[], review_fact_ids={"f3", "f7"})
        assert len(calls) == 1  # One selected review batch; no second evidence-planning/summarising call.
        assert [row["id"] for row in calls[0]["evidence"]["facts"]] == ["f3", "f7"]
        assert [row["id"] for row in result["facts"]] == [row["id"] for row in facts]
        assert result["executive_summary"] == brief["executive_summary"]
        await memo._run_evidence_reconciliation(query="neutral", mode="deep", evidence_briefs=[result], asset_class_vocabulary=[], review_fact_ids={"f3", "f7"})
        assert len(calls) == 1
    finally:
        CURRENT_RUNTIME.reset(token)
    checks = {key: "supported" for key in FACT_FIELDS}
    checks["published_at"] = "unresolved"
    checked = apply_fact_checks([fact], [{"fact_id": fact["id"], "checks": checks, "reason": "Publication date unknown"}], packet)[0]
    assert checked["review_dimensions"]["observation"] == "supported"
    assert checked["review_dimensions"]["publication_metadata"] == "unresolved"


@pytest.mark.asyncio
async def test_successful_detail_batches_survive_another_batch_failure(monkeypatch):
    runtime = PortfolioRuntime()
    responses = [
        {"content": json.dumps({"allocation_details": [{"asset_class": f"A{i}", "investment_case": {"downside": "Retained downside"}} for i in range(4)]}), "stage_status": "complete"},
        {"content": "", "stage_status": "failed", "error": "Supplementary provider unavailable"},
    ]
    runtime.query = AsyncMock(side_effect=responses)
    proposal = {"asset_class_targets": [target(f"A{i}", 20) for i in range(5)]}
    result = await memo._enrich_allocation("test/model", {"content": json.dumps(proposal)}, {"task": "Test investment cases"}, runtime=runtime)
    retained = json.loads(result["content"])
    assert retained["asset_class_targets"][0]["investment_case"]["downside"] == "Retained downside"
    assert len(retained["asset_class_targets"]) == 5 and result["warnings"]


def test_detail_work_is_for_new_changed_or_challenged_exposures():
    from backend.portfolio_independent import material_detail_targets
    proposal = {"asset_class_targets": [target("ENERGY", 35), target("CASH", 65)]}
    assert material_detail_targets(snapshot(), proposal, []) == []
    reviewed = material_detail_targets(snapshot(), proposal, [{"findings": [{"asset_class": "ENERGY", "argument": "Margin uncertainty"}]}])
    assert [row["asset_class"] for row in reviewed] == ["ENERGY"]
    proposal["asset_class_targets"] = [target("NOVEL", 100)]
    assert material_detail_targets(snapshot(), proposal, [])[0]["asset_class"] == "NOVEL"


@pytest.mark.parametrize("count", [1, 7, 24])
def test_ideal_universe_does_not_pad_to_current_holdings(count):
    prompt = allocation_prompt("blind_macro_prior", evidence(), independent_context({}, CUTOFF))
    proposal, _ = recover_optional_fields({"asset_class_targets": [target(f"NEW_{i}", 100 / count) for i in range(count)]}, prompt)
    assert not validate_independent_stage(proposal, prompt)
    rendered = render_portfolio_memo(snapshot=snapshot(), structured={"independent_ideal": proposal}, evidence_brief=evidence(), citations=[])
    assert "Energy" not in rendered
    assert len(proposal["asset_class_targets"]) == count


@pytest.mark.asyncio
@pytest.mark.parametrize("version", [3, 4])
async def test_new_play_assessment_links_source_without_mutating_it(tmp_path, monkeypatch, version):
    from backend.routers.analysis_jobs import _portfolio_source
    from backend.jobs.executor import CreateAnalysisJobRequest, _build_analysis_job_command
    from backend.jobs import runs
    original = {"workflow_version": version, "portfolio_context": snapshot(),
        "portfolio_snapshot": {**snapshot(), "company_evidence": [{"ticker": "ASX:TEST"}]}, "query": "Saved research query"}
    path = tmp_path / "original.json"
    path.write_text(json.dumps(original))
    checkpoint = path.with_suffix(".checkpoint.json")
    checkpoint.write_text(json.dumps({"workflow_version": version}))
    monkeypatch.setattr(runs, "_resolve_portfolio_positioning_artifact_path", lambda name: path)
    request = CreateAnalysisJobRequest(job_type="portfolio_positioning", reassess_portfolio_run_id=path.name,
        investment_plays=[{"title": "New idea", "thesis": "Test it"}])
    await _portfolio_source(request)
    assert request.portfolio_context["source_run_id"] == path.name
    assert request.portfolio_context["investment_plays"][0]["title"] == "New idea"
    assert request.portfolio_context["frozen_research_query"] == original["query"]
    assert request.portfolio_context["frozen_company_evidence"] == original["portfolio_snapshot"]["company_evidence"]
    assert json.loads(path.read_text()) == original
    command = _build_analysis_job_command(request, tmp_path / "new.json", portfolio_context_path=tmp_path / "context.json")
    assert command[command.index("--resume-checkpoint") + 1] == str(checkpoint)
    checkpoint.write_text('{"workflow_version":2}')
    assert "--resume-checkpoint" not in _build_analysis_job_command(request, tmp_path / "new.json", portfolio_context_path=tmp_path / "context.json")


@pytest.mark.asyncio
@pytest.mark.parametrize("version", [3, 4])
async def test_baseline_preserving_reassessment_accepts_independent_workflows(tmp_path, monkeypatch, version):
    from backend.routers.analysis_jobs import _portfolio_source
    from backend.jobs.executor import CreateAnalysisJobRequest, _build_analysis_job_command
    from backend.jobs import runs
    from backend.portfolio_repair import load_frozen_baselines
    from fastapi import HTTPException

    original = {"workflow_version": version, "portfolio_context": snapshot(),
        "independent_ideal": {"asset_class_targets": [target("CASH", 100)]},
        "current_portfolio_assessment": {"asset_class_targets": [target("ENERGY", 100)]},
        "evidence_brief": evidence()}
    path = tmp_path / "original.json"
    path.write_text(json.dumps(original))
    checkpoint = path.with_suffix(".checkpoint.json")
    checkpoint.write_text(json.dumps({"workflow_version": version}))
    monkeypatch.setattr(runs, "_resolve_portfolio_positioning_artifact_path", lambda name: path)
    request = CreateAnalysisJobRequest(job_type="portfolio_positioning", reassess_portfolio_run_id=path.name,
        preserve_portfolio_baselines=True, investment_plays=[{"title": "New idea", "thesis": "Test it"}])
    await _portfolio_source(request)
    frozen = load_frozen_baselines(request.portfolio_context, checkpoint)
    for field in ("independent_ideal", "current_portfolio_assessment", "evidence_brief"):
        assert frozen[field] == original[field]
    command = _build_analysis_job_command(request, tmp_path / "new.json", portfolio_context_path=tmp_path / "context.json")
    assert command[command.index("--resume-checkpoint") + 1] == str(checkpoint)
    assert json.loads(path.read_text()) == original
    checkpoint.unlink()
    with pytest.raises(HTTPException) as missing:
        await _portfolio_source(request)
    assert missing.value.status_code == 409
    checkpoint.write_text('{"workflow_version":2}')
    path.write_text(json.dumps({**original, "workflow_version": 2}))
    with pytest.raises(HTTPException) as legacy:
        await _portfolio_source(request)
    assert legacy.value.status_code == 409


@pytest.mark.asyncio
async def test_new_run_play_inputs_and_original_recovery_are_distinct():
    from backend.routers.analysis_jobs import _portfolio_source
    from backend.jobs.executor import CreateAnalysisJobRequest
    from fastapi import HTTPException
    request = CreateAnalysisJobRequest(portfolio_context=snapshot(), investment_plays=[{"title": "Test", "thesis": "Hypothesis"}])
    await _portfolio_source(request)
    assert request.portfolio_context["investment_plays"][0]["id"].startswith("play_")
    request.resume_portfolio_run_id = "old.json"
    with pytest.raises(HTTPException, match="Recovery preserves"):
        await _portfolio_source(request)
