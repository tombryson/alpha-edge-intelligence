import json
from copy import deepcopy
from unittest.mock import AsyncMock

import httpx
import pytest

import portfolio_positioning_memo as memo
from backend.portfolio_independent import freeze_play_components, complete_play_assessments, independent_context
from backend.portfolio_judgment import (calculate_financial_claims, implementation_comparison, apply_claim_patches,
    retain_current_details, detail_basis, financial_comparison_issues)
from backend.portfolio_memo import render_portfolio_memo
from backend.portfolio_research import (
    CONTRACT, coverage, normalize_questions, planning_prompt, provider_context, qualify_research_dependencies,
)
from backend.portfolio_retrieval import ParallelSourceProvider, ResearchBudget, normalize_result
from backend.portfolio_runtime import CURRENT_RUNTIME, PortfolioRuntime


def question(**updates):
    return {"question": "What do measured Gulf production and exports establish about restored supply?",
        "topic": "oil", "economic_question": "physical_balance", "geography": "global", "period": "September 2026",
        "horizon": "12 months", "required_dimensions": ["production", "exports"], "status": "unanswered",
        "material_reason": "Changes the supply-normalisation premise", "reuse_assessment": "Prices alone do not establish physical availability",
        "asset_classes": ["oil_producers"], "decision_impact": "high", "critical_premise": True, **updates}


def evidence():
    return {"evidence_status": "complete", "facts": [
        {"id": "flow", "kind": "observed_macro", "metric": "Gulf output shut in", "value": 10,
         "unit": "million barrels/day", "benchmark": "Gulf production", "currency": "not_applicable",
         "observed_at": "2026-08-31", "published_at": "2026-09-11", "source_ids": ["primary"]}],
        "source_packet": {"as_of": "2026-09-19T03:04:58Z", "sources": [
            {"id": "primary", "url": "https://example.org/physical-balance", "excerpt": "Output remains disrupted.", "published_at": "2026-09-11"}]}}


def test_blind_plan_is_independent_of_holdings_and_user_plays():
    secret = {"asset_classes": [{"asset_class": "PRIVATE_HOLDING", "portfolio_pct": 33.7}], "investment_plays": [{"thesis": "PRIVATE_IDEA"}]}
    neutral = independent_context(secret, "2026-09-19")
    prompt = planning_prompt("independent", evidence(), neutral)
    assert "PRIVATE_" not in json.dumps(prompt)
    assert "current_portfolio" not in prompt and "investment_plays" not in prompt
    current = planning_prompt("current", evidence(), neutral, holdings={"current_asset_classes": secret["asset_classes"]})
    assert "independent_ideal" not in current and "investment_plays" not in current
    assert "borrow another fund" not in memo._build_evidence_lane_specs("neutral", "deep")[2]["focus"]
    assert not memo._build_evidence_lane_specs("neutral", "deep")[2]["include_coverage_checklist"]


def test_provider_context_contains_economics_not_portfolio_or_diagnostic_checklists():
    row = question(existing_fact_ids=["flow"], material_reason="Our private 33.7% holding", portfolio={"SECRET": 100})
    context = provider_context(row, evidence())
    assert context["known_observations"][0]["value"] == 10
    assert "33.7" not in json.dumps(context) and "SECRET" not in json.dumps(context)
    assert context["required_dimensions"] == ["production", "exports"]


def test_question_paraphrases_share_identity_but_distinct_periods_do_not():
    rows = normalize_questions([question(), question(question="How much oil is actually available?", required_dimensions=["inventories"]),
                                question(period="March 2026")], evidence())
    assert len(rows) == 2
    assert rows[0]["required_dimensions"] == ["production", "exports", "inventories"]
    assert rows[0]["id"] != rows[1]["id"]
    assert normalize_questions([question(question="A material question " * 30)], evidence())


def test_equal_priority_preserves_planner_order_without_per_asset_quota():
    rows = normalize_questions([question(economic_question="oil_output"), question(economic_question="oil_contracts"),
        question(topic="fertiliser", economic_question="fertiliser_margins", asset_classes=["fertiliser_producers"])])
    assert [row["topic"] for row in rows] == ["oil", "oil", "fertiliser"]


def test_existing_fact_ids_do_not_establish_answer_coverage():
    row = question(status="answered", existing_fact_ids=["flow"])
    assert normalize_questions([row], evidence())[0]["status"] == "unanswered"
    answers = [{"dimension": "production", "answer": "Production remains shut in", "status": "answered", "fact_ids": ["flow"]}]
    checked = coverage(row, evidence(), answers)
    assert checked["status"] == "partial" and checked["missing_dimensions"] == ["exports"]
    answers.append({"dimension": "exports", "answer": "Invented restoration", "status": "answered", "fact_ids": ["missing"]})
    assert coverage(row, evidence(), answers)["status"] == "partial"


def test_metadata_uncertainty_does_not_erase_an_observation_but_contradicted_values_do():
    brief = evidence()
    answers = [{"dimension": "production", "answer": "Measured disruption", "status": "answered", "fact_ids": ["flow"]}]
    row = question(required_dimensions=["production"])
    brief["facts"][0]["review_dimensions"] = {"observation": "supported", "publication_metadata": "unresolved"}
    assert coverage(row, brief, answers)["status"] == "answered"
    brief["facts"][0]["review_dimensions"]["observation"] = "unsupported"
    assert coverage(row, brief, answers)["status"] == "unanswered"


def plays():
    return [{"id": "p", "title": "Scarcity", "thesis": "Fertiliser and uranium producers"}]


def test_shared_source_sentence_cannot_overwrite_another_play_component():
    inventory = [{"play_id": "p", "components": [{"economic_key": name.lower(), "name": name, "source_text": plays()[0]["thesis"], "direction": "long"}
        for name in ("Fertiliser", "Uranium")]}]
    frozen = freeze_play_components(plays(), inventory)
    assert len(frozen[0]["components"]) == 2
    a, b = frozen[0]["components"]
    assert a["id"] != b["id"]
    rows = [{"play_id": "p", "score": 7, "verdict": "watch", "legs": [
        {"component_id": b["id"], "name": "Uranium", "source_text": b["source_text"], "mechanism": "Fuel contracting", "score": 7, "verdict": "watch"}]}]
    result = complete_play_assessments(frozen, rows)[0]
    assert result["legs"][0]["assessment_status"] == "missing"
    assert result["legs"][1]["mechanism"] == "Fuel contracting"
    rows[0]["legs"][0]["component_id"] = a["id"]
    result = complete_play_assessments(frozen, rows)[0]
    assert result["unmatched_legs"]
    assert "mechanism" not in result["legs"][0]


def test_critical_missing_research_qualifies_only_the_affected_leg_and_keeps_allocation():
    row = normalize_questions([question(play_ids=["p"], component_ids=["oil"])])[0]
    original = {"asset_class_targets": [{"asset_class": "oil_producers", "target_pct": 14}], "play_assessments": [
        {"play_id": "p", "score": 5, "verdict": "watch", "legs": [
            {"component_id": "oil", "score": 4, "verdict": "watch", "mechanism": "Saved reasoning"},
            {"component_id": "gold", "score": 8, "verdict": "include"}]}]}
    result = qualify_research_dependencies(original, {"research_questions": [row]})
    assert result["asset_class_targets"][0]["target_pct"] == 14
    assert result["asset_class_targets"][0]["research_gaps"][0]["question_id"] == row["id"]
    assert "action_readiness" not in result["asset_class_targets"][0]
    oil, gold = result["play_assessments"][0]["legs"]
    assert oil["score"] == 4 and oil["reported_judgment"]["score"] == 4 and oil["mechanism"]
    assert oil["assessment_status"] == "provisional" and oil["confidence"] == "low"
    assert result["play_assessments"][0]["score"] == 5
    assert gold["score"] == 8
    assert original["play_assessments"][0]["legs"][0]["score"] == 4


def test_research_dependency_survives_a_different_exposure_name():
    item = normalize_questions([question()])[0]
    original = {"asset_class_targets": [{"asset_class": "US_ENERGY_EQUITIES", "target_pct": 12,
        "research_question_ids": [item["id"]]}]}
    result = qualify_research_dependencies(original, {"research_questions": [item]})
    assert result["asset_class_targets"][0]["research_gaps"][0]["question_id"] == item["id"]
    assert "action_readiness" not in result["asset_class_targets"][0]
    assert result["asset_class_targets"][0]["target_pct"] == 12


@pytest.mark.asyncio
async def test_parallel_credit_failure_stops_new_submissions_but_resume_can_retry(tmp_path):
    posts = []
    def rejected(request):
        posts.append(request)
        return httpx.Response(402, json={"error": {"message": "Insufficient credit"}})
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    provider = ParallelSourceProvider(api_key="test", processor="ultra4x", transport=httpx.MockTransport(rejected))
    await provider.gather(runtime, question="Oil balance?", context={"period": "September"})
    await provider.gather(runtime, question="Fertiliser margins?", context={"period": "September"})
    assert len(posts) == 1
    assert runtime.receipts[-1]["status"] == "failed" and runtime.receipts[-1]["optional"]
    assert all(phase["completed"] == 0 for phase in runtime.progress.snapshot()["phases"])
    assert runtime.progress.snapshot()["research_failures"] == 2
    assert ResearchBudget(runtime).remaining == ResearchBudget(runtime).limit
    restored = PortfolioRuntime(tmp_path / "resumed.json", resume=runtime.checkpoint)
    await provider.gather(restored, question="Oil balance?", context={"period": "September"})
    assert len(posts) == 2


def test_source_selection_covers_answer_dimensions_instead_of_first_five_urls():
    urls = [f"https://example.org/{i}" for i in range(6)]
    packet = {"output": {"content": {"sources": [{"url": url} for url in urls],
        "answer_dimensions": [{"dimension": "physical flows", "answer": "Measured flows", "status": "answered", "source_urls": [urls[-1]]}]},
        "basis": [{"field": "sources", "citations": [{"url": url, "excerpts": ["Evidence"]} for url in urls]}]}}
    result = normalize_result(packet)
    assert len(result["results"]) == 5
    assert result["results"][0]["url"] == urls[-1]
    assert len(result["raw_response"]["output"]["content"]["sources"]) == 6


def yield_fact(identifier, maturity, value, **fields):
    return {"id": identifier, "metric": f"{maturity}-year Treasury yield", "benchmark": f"US {maturity}-year Treasury yield",
        "value": value, "unit": "%", "currency": "USD", "observed_at": "2026-09-18", "vintage": "September",
        "measurement": {"price_basis": "nominal", "horizon_months": maturity * 12, "curve": "US Treasury"}, **fields}


def test_curve_spread_uses_different_maturities_and_reports_basis_points():
    facts = [yield_fact("ten", 10, 5.01), yield_fact("two", 2, 4.76)]
    result = calculate_financial_claims({"calculations": [{"operation": "curve_spread", "fact_ids": ["ten", "two"]}]}, {"facts": facts})[0]
    assert result["computed_value"] == .25 and result["basis_points"] == 25
    assert result["unit"] == "percentage_points"
    assert not financial_comparison_issues({"financial_comparisons": [{"operation": "curve_spread",
        "left_fact_id": "ten", "right_fact_id": "two"}]}, {"facts": facts})
    facts[1]["measurement"]["curve"] = "Corporate BBB"
    assert calculate_financial_claims({"calculations": [{"operation": "curve_spread", "fact_ids": ["ten", "two"]}]}, {"facts": facts})[0]["computed_value"] is None


def test_time_change_allows_different_dates_but_not_instruments():
    first = yield_fact("now", 10, 5.01)
    previous = yield_fact("before", 10, 4.8, observed_at="2026-08-18", vintage="August")
    previous["measurement"]["reference_period"] = "August"
    first["measurement"]["reference_period"] = "September"
    claim = {"calculations": [{"operation": "time_change", "fact_ids": ["now", "before"]}]}
    assert calculate_financial_claims(claim, {"facts": [first, previous]})[0]["basis_points"] == 21
    previous["benchmark"] = "US 2-year Treasury yield"
    assert calculate_financial_claims(claim, {"facts": [first, previous]})[0]["status"] == "unresolved"


def test_breakeven_requires_same_maturity_and_nominal_minus_real():
    nominal, real = yield_fact("nominal", 10, 5), yield_fact("real", 10, 2)
    real["measurement"]["price_basis"] = "real"
    result = calculate_financial_claims({"calculations": [{"operation": "breakeven_spread", "fact_ids": ["nominal", "real"]}]},
        {"facts": [nominal, real]})[0]
    assert result["basis_points"] == 300
    real["measurement"]["horizon_months"] = 24
    assert calculate_financial_claims({"calculations": [{"operation": "breakeven_spread", "fact_ids": ["nominal", "real"]}]},
        {"facts": [nominal, real]})[0]["status"] == "unresolved"


def test_reviewed_correction_survives_detail_reuse_but_changed_weights_do_not():
    row = {"asset_class": "bonds", "target_pct": 14, "detail_status": "current", "rationale": "Wrong comparison",
        "investment_case": {"why_better_than_hold": "Fixed-rate bonds lose value when yields fall"}}
    row["detail_evidence_hash"] = detail_basis(row, evidence())
    original = {"asset_class_targets": [row]}
    review = {"patches": [{"path": ["asset_class_targets", 0, "investment_case", "why_better_than_hold"],
        "original": row["investment_case"]["why_better_than_hold"], "replacement": "Falling yields raise prices, other things equal.",
        "reason": "Distinguish price return from reinvestment income", "fact_ids": []},
        {"path": ["asset_class_targets", 0, "rationale"], "original": "Wrong comparison", "replacement": "14% exceeds the 11% cash weight.",
         "reason": "Recorded weights", "fact_ids": []}]}
    corrected = apply_claim_patches(original, review, evidence())
    retained, stale = retain_current_details(corrected, original, evidence())
    assert not stale and "Falling yields raise prices" in retained["asset_class_targets"][0]["investment_case"]["why_better_than_hold"]
    corrected["asset_class_targets"][0]["target_pct"] = 9
    _, stale = retain_current_details(corrected, retained, evidence())
    assert stale and stale[0]["previous_investment_details"]["investment_case"]


def test_unknown_publication_metadata_does_not_disprove_reviewed_observation():
    from backend.portfolio_evidence import apply_fact_checks, FACT_FIELDS, fact_is_supported, fact_observation_is_supported
    brief = evidence()
    fact = {**brief["facts"][0], "published_at": None, "vintage": None, "source_excerpt": "Output remains disrupted by 10 million barrels/day."}
    brief["source_packet"]["sources"][0]["excerpt"] = fact["source_excerpt"]
    check = {"fact_id": "flow", "checks": {field: "supported" if field not in {"published_at", "vintage"} else "unresolved" for field in FACT_FIELDS},
        "reason": "Observation is supported; publication version remains unknown."}
    reviewed = apply_fact_checks([fact], [check], brief["source_packet"])[0]
    assert fact_observation_is_supported(reviewed) and not fact_is_supported(reviewed)
    check["checks"]["value"] = "unsupported"
    assert not fact_observation_is_supported(apply_fact_checks([fact], [check], brief["source_packet"])[0])


def test_after_cutoff_or_unmatched_source_does_not_complete_question():
    brief = evidence()
    brief["facts"][0]["verification_issues"] = ["Referenced source was published after the research cutoff"]
    answers = [{"dimension": "production", "status": "answered", "answer": "Later information", "fact_ids": ["flow"]}]
    assert coverage(question(required_dimensions=["production"]), brief, answers)["status"] == "unanswered"


def test_smaller_change_explicitly_retains_unmentioned_weights():
    snapshot = {"portfolio": {"cash_pct": 10}, "asset_classes": [
        {"asset_class": "gold", "portfolio_pct": 40}, {"asset_class": "oil", "portfolio_pct": 50}]}
    def target(name, weight):
        return {"asset_class": name, "min_pct": weight, "max_pct": weight, "target_pct": weight}
    proposal = {"asset_class_targets": [target("gold", 50), target("oil", 30), target("cash", 20)],
        "smaller_change_alternative": {"retain_unmentioned": True, "asset_class_targets": [target("oil", 45), target("cash", 15)]}}
    comparison = implementation_comparison(snapshot, proposal, {})
    assert comparison["smaller_change"]["funding"]["status"] == "balanced"
    assert comparison["smaller_change"]["funding"]["one_way_turnover_pct"] == 5
    assert not comparison["issues"]
    proposal["smaller_change_alternative"]["retain_unmentioned"] = False
    assert implementation_comparison(snapshot, proposal, {})["issues"]


def test_monitoring_uses_available_source_observations_and_not_forecasts():
    brief = evidence()
    proposal = {"asset_class_targets": [], "monitoring_triggers": [
        {"metric": "Gulf output shut in", "benchmark": "Gulf production", "unit": "million barrels/day", "operator": "gt", "threshold": 5, "max_age_days": 31}],
        "forecasts": [{"metric": "Portfolio weight in oil", "value": 14}, {"metric": "Oil demand", "value": 100}]}
    result = implementation_comparison({}, proposal, brief)
    assert result["review_conditions"][0]["status"] == "unassessed"
    assert len(result["forecasts"]) == len(result["allocation_intentions"]) == 1
    from backend.portfolio_evidence import apply_fact_checks, review_fields
    brief["facts"][0]["source_excerpt"] = brief["source_packet"]["sources"][0]["excerpt"] = "Gulf output shut in: 10 million barrels/day, observed 31 August 2026."
    brief["facts"] = apply_fact_checks(brief["facts"], [{"fact_id": "flow", "reason": "Exact observation",
        "checks": {key: "supported" for key in review_fields(brief["facts"][0])}}], brief["source_packet"])
    assert implementation_comparison({}, proposal, brief)["review_conditions"][0]["status"] == "triggered"
    brief["facts"][0]["kind"] = "forecast"
    assert implementation_comparison({}, proposal, brief)["review_conditions"][0]["status"] == "unassessed"


@pytest.mark.asyncio
async def test_question_research_retains_results_and_does_not_exclude_previously_seen_urls(tmp_path, monkeypatch):
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    runtime.partial["research_phases"] = [{"phase": "earlier"}]
    gather = AsyncMock(return_value={"provider": "parallel", "question_status": "answered", "results": [
        {"url": "https://example.org/physical-balance", "content": "Measured output and export constraints."}]})
    monkeypatch.setattr(ParallelSourceProvider, "gather", gather)
    async def structure(lane, **kwargs):
        lane["evidence_brief"] = {**evidence(), "question_answers": [
            {"dimension": dimension, "answer": "Dated physical observation", "status": "answered", "fact_ids": ["flow"]}
            for dimension in lane["question"]["required_dimensions"]]}
        return lane
    monkeypatch.setattr(memo, "_structure_evidence_lane", structure)
    token = CURRENT_RUNTIME.set(runtime)
    try:
        brief, runs, report = await memo._run_question_research(evidence(), "deep", {
            "phase": "independent", "research_contract": CONTRACT, "questions": [question(existing_fact_ids=["flow"])]})
        assert report["answered"] == 1
        assert brief["research_questions"][0]["status"] == "answered"
        assert len(runs) == 1
        assert not gather.call_args.kwargs.get("exclude_urls")
        assert gather.call_args.kwargs["context"]["known_observations"]
        assert "independent" in runtime.partial["research_phase_results"]
        _, again, replay = await memo._run_question_research(brief, "deep", {
            "phase": "current", "research_contract": CONTRACT, "questions": [question(existing_fact_ids=["flow"])]})
        assert not again and replay["answered"] == 1 and gather.await_count == 1
    finally:
        CURRENT_RUNTIME.reset(token)


@pytest.mark.asyncio
async def test_partial_research_is_not_marked_answered_by_provider_self_report(tmp_path, monkeypatch):
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    monkeypatch.setattr(ParallelSourceProvider, "gather", AsyncMock(return_value={"provider": "parallel", "question_status": "answered",
        "results": [{"url": "https://example.org/news", "content": "Supply anxiety eased."}]}))
    async def structure(lane, **kwargs):
        lane["evidence_brief"] = evidence()  # No dimension-specific answer established.
        return lane
    monkeypatch.setattr(memo, "_structure_evidence_lane", structure)
    token = CURRENT_RUNTIME.set(runtime)
    try:
        brief, _, report = await memo._run_question_research(evidence(), "deep", {"phase": "plays", "questions": [question()]})
        assert report["answered"] == 0 and report["status"] == "with_limitations"
        assert brief["facts"] and brief["evidence_status"] == "complete"
    finally:
        CURRENT_RUNTIME.reset(token)


@pytest.mark.asyncio
async def test_exhausted_budget_resumes_paid_question_without_another_post(tmp_path, monkeypatch):
    monkeypatch.setenv("PORTFOLIO_RESEARCH_BUDGET_USD", "1.20")
    posts = []
    def handler(request):
        if request.method == "POST":
            posts.append(request)
            return httpx.Response(202, json={"run_id": "trun_saved", "status": "queued"})
        if request.url.path.endswith("/result"):
            return httpx.Response(200, json={"run": {"processor": "ultra4x", "run_id": "trun_saved"}, "output": {
                "content": {"summary": "Retained research", "sources": [{"url": "https://example.org/saved"}]},
                "basis": [{"citations": [{"url": "https://example.org/saved", "excerpts": ["Original source text"]}]}]}})
        return httpx.Response(200, json={"status": "completed"})
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    task = normalize_questions([question()], evidence())[0]
    provider = ParallelSourceProvider(api_key="test", processor="ultra4x", transport=httpx.MockTransport(handler), timeout_seconds=0)
    await provider.gather(runtime, question=task["question"], context=provider_context(task, evidence()), deep_research=True)
    assert ResearchBudget(runtime).remaining == 0 and len(posts) == 1
    resumed = PortfolioRuntime(tmp_path / "resume.json", resume=runtime.checkpoint)
    provider.timeout_seconds = 10
    monkeypatch.setattr(memo, "ParallelSourceProvider", lambda: provider)
    async def structure(lane, **kwargs):
        lane["evidence_brief"] = {**evidence(), "question_answers": [
            {"dimension": dimension, "answer": "Measured constraints", "status": "answered", "fact_ids": ["flow"]}
            for dimension in task["required_dimensions"]]}
        return lane
    monkeypatch.setattr(memo, "_structure_evidence_lane", structure)
    token = CURRENT_RUNTIME.set(resumed)
    try:
        _, runs, report = await memo._run_question_research(evidence(), "deep", {"phase": "independent", "questions": [task]})
        assert report["answered"] == 1 and runs
        assert len(posts) == 1 and report["budget"]["reserved_estimate_usd"] == 1.20
    finally:
        CURRENT_RUNTIME.reset(token)


@pytest.mark.asyncio
async def test_extraction_failure_retains_the_paid_sources_and_other_answers(tmp_path, monkeypatch):
    gather = AsyncMock(return_value={"provider": "parallel", "expansion_query": "What are the remaining flows?", "results": [
        {"url": "https://example.org/saved", "content": "Saved original evidence"}]})
    monkeypatch.setattr(ParallelSourceProvider, "gather", gather)
    async def structure(lane, **kwargs):
        if lane["question"]["topic"] == "oil":
            raise ValueError("Extraction unavailable")
        lane["evidence_brief"] = {**evidence(), "question_answers": [
            {"dimension": dimension, "answer": "Measured constraints", "status": "answered", "fact_ids": ["flow"]}
            for dimension in lane["question"]["required_dimensions"]]}
        return lane
    monkeypatch.setattr(memo, "_structure_evidence_lane", structure)
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    token = CURRENT_RUNTIME.set(runtime)
    try:
        result, runs, report = await memo._run_question_research(evidence(), "deep", {"phase": "plays", "questions": [question(),
            question(topic="fertiliser", economic_question="feedstock_cost", asset_classes=["fertiliser"])]})
        assert report["answered"] == 1 and len(runs) == 2 and result["facts"]
        assert runs[0]["parallel"]["results"][0]["content"] == "Saved original evidence"
        assert "Extraction unavailable" in report["questions"][0]["reason"]
        assert report["questions"][0]["retrieval_status"] == "succeeded"
        assert report["questions"][0]["processing_status"] == "failed" and gather.await_count == 2
    finally:
        CURRENT_RUNTIME.reset(token)


def test_research_led_memo_leads_with_decision_and_keeps_appendix_late():
    structured = {"workflow_version": 4, "executive_summary": "A conditional investment view.",
        "asset_class_targets": [{"asset_class": "cash", "target_pct": 11, "rationale": "Preserve optionality."}],
        "independent_ideal": {"executive_summary": "Independent view", "asset_class_targets": [{"asset_class": "cash", "target_pct": 12}]},
        "current_portfolio_assessment": {"executive_summary": "Current view"}}
    markdown = render_portfolio_memo(snapshot={"portfolio": {"cash_pct": .425997}}, structured=structured, evidence_brief=evidence(), citations=[])
    assert markdown.index("Recommended Portfolio") < markdown.index("Supporting Research") < markdown.index("Independent Ideal Portfolio")
    assert "0.43%" in markdown and "0.425997" not in markdown
    assert markdown.count("Preserve optionality.") == 1
    assert "fact_ids" not in markdown
    original = deepcopy(structured)
    render_portfolio_memo(snapshot={}, structured=structured, evidence_brief=evidence(), citations=[])
    assert original == structured


def test_answered_research_retires_stale_gaps_without_changing_the_recommendation():
    from backend.portfolio_decisions import build_decision
    from backend.portfolio_research import research_readthrough
    brief = evidence()
    item = normalize_questions([question(required_dimensions=["production"],
        decision_consequence="Changes the production assumption, not the concentration limit.")], brief)[0]
    brief["research_questions"] = [item]
    brief["unresolved_market_questions"] = [deepcopy(item)]
    original = {"asset_class_targets": [{"asset_class": "oil_producers", "target_pct": 14,
        "rationale": "Reduce concentration; this is not a bearish supply forecast.",
        "action_basis": {"category": "risk", "reason": "Concentration", "evidence_status": "supported"}}]}
    pending = qualify_research_dependencies(original, brief)
    pending["asset_class_targets"][0]["action_readiness"] = "conditional"  # Old saved proposal.
    item["answers"] = [{"dimension": "production", "status": "answered", "answer": "Measured disruption remains.", "fact_ids": ["flow"]}]
    updated = qualify_research_dependencies(pending, brief)
    assert updated == original
    assert pending["asset_class_targets"][0]["research_gaps"]  # No mutation of history.
    assert item["status"] == "unanswered"  # Saved status is not trusted over validated answers.
    decision = build_decision({}, updated, brief)
    assert not decision["funding"]["rows"][0].get("unanswered_market_questions")
    assert research_readthrough(brief)[0]["decision_consequence"] == item["decision_consequence"]
    brief["facts"][0]["review_dimensions"] = {"observation": "unsupported"}
    disputed = qualify_research_dependencies(updated, brief)
    assert disputed["asset_class_targets"][0]["research_gaps"][0]["status"] == "unanswered"
    assert disputed["asset_class_targets"][0]["rationale"] == original["asset_class_targets"][0]["rationale"]


def test_memo_keeps_questions_in_research_and_preserves_decision_specific_caveats():
    brief = evidence()
    answered = normalize_questions([question(required_dimensions=["production"], answers=[
        {"dimension": "production", "status": "answered", "answer": "Measured disruption remains.", "fact_ids": ["flow"]}])], brief)[0]
    answered["status"] = "unanswered"
    partial = normalize_questions([question(period="2027", required_dimensions=["production", "exports"], answers=answered["answers"])], brief)[0]
    brief["research_questions"] = [answered, partial, {"question": "A historical question without an identifier?"}]
    rationale = "Reduce concentration. Individual producer valuations are not established; this is a risk decision, not a cheapness claim."
    proposal = {"workflow_version": 4, "asset_class_targets": [{"asset_class": "oil_producers", "target_pct": 14,
        "rationale": rationale, "action_readiness": "conditional", "research_gaps": [
            {"question_id": answered["id"], "question": answered["question"]},
            {"question_id": "legacy", "question": "Which held producer has a secure balance sheet?"},
            {"question_id": "legacy", "question": "Which held producer has a secure balance sheet?"}]}],
        "monitoring_triggers": ["Reconsider if producer funding deteriorates."]}
    original = deepcopy(proposal)
    markdown = render_portfolio_memo(snapshot={}, structured=proposal, evidence_brief=brief, citations=[])
    main, supporting = markdown.split("## Supporting Research", 1)
    assert rationale in main and "Reconsider if producer funding deteriorates." in main
    assert "Any change remains conditional" not in markdown
    assert answered["question"] not in main and "Which held producer" not in main
    assert supporting.count("Measured disruption remains.") == 1
    assert supporting.count("Still unresolved:") == 2  # Distinct 2027 scope and historical question.
    assert "Still unresolved: exports" in supporting
    assert supporting.count("Which held producer has a secure balance sheet?") == 1
    assert proposal == original
