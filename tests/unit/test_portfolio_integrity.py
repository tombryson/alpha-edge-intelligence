import argparse
import copy
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from backend.portfolio_decisions import (analysis_health, build_decision, evaluate_conditions,
    funding_ledger, scenario_comparison, shadow_returns, forecast_calibration)
from backend.portfolio_evidence import merge_briefs, normalize_facts, validate_stage
from backend.portfolio_runtime import PortfolioRuntime, business_data, CURRENT_RUNTIME
import portfolio_positioning_memo as memo


@pytest.fixture(autouse=True)
def no_live_models(monkeypatch):
    monkeypatch.setattr(memo, "query_model", AsyncMock(side_effect=AssertionError("Live model calls are forbidden in unit tests")))


def snapshot():
    return {"as_of": "2026-08-11T00:00:00Z", "portfolio": {"cash_pct": 20, "total_value": 100000},
        "asset_classes": [{"asset_class": "equity", "portfolio_pct": 80}],
        "mandate": {"base_currency": "AUD", "benchmark": "cash", "horizon_months": 12,
                    "max_drawdown_pct": 20, "liquidity_min_pct": 10, "tax_cost_policy": "Tax assessed separately", "currency_hedge_policy": "Fully hedged"}}


def proposal(equity=60):
    return {"asset_class_targets": [{"asset_class": asset, "min_pct": weight, "target_pct": weight, "max_pct": weight}
        for asset, weight in (("equity", equity), ("cash", 100 - equity))]}


def packet():
    return {"as_of": "2026-08-11T00:00:00Z", "sources": [{"id": "s1", "url": "https://example.org/release", "excerpt": "GDP growth was 3.1 percent."}], "research": []}


def fact():
    return {"id": "f1", "kind": "observed_macro", "metric": "growth", "value": 3.1, "unit": "percent", "currency": "not_applicable",
        "benchmark": "Example GDP model", "vintage": "initial", "observed_at": "2026-08-01", "published_at": "2026-08-10",
        "source_ids": ["s1"], "source_excerpt": "GDP growth was 3.1 percent."}


def test_funding_conservation_and_no_gap_conviction():
    decision = build_decision(snapshot(), proposal(), {})
    assert decision["funding"]["status"] == "balanced"
    assert sum(row["trade_pct"] for row in decision["funding"]["rows"]) == 0
    assert decision["funding"]["one_way_turnover_pct"] == 20
    assert all(row["conviction"] == "UNASSESSED" for row in decision["funding"]["rows"])


def test_omitted_sleeve_does_not_create_107_percent_or_fake_hold():
    context = snapshot()
    context["asset_classes"] = [{"asset_class": "equity", "portfolio_pct": 72.77}, {"asset_class": "miners", "portfolio_pct": 7.23}]
    proposed = proposal()
    proposed["current_sleeve_actions"] = [{"asset_class": "miners", "action": "TRIM"}]
    ledger = funding_ledger(context, proposed)
    assert ledger["status"] == "unresolved"
    assert ledger["rows"][-1]["target_pct"] is None
    proposed["current_sleeve_actions"][0]["action"] = "HOLD"
    assert funding_ledger(context, proposed)["specified_target_total_pct"] == 107.23
    proposed["current_sleeve_actions"][0]["action"] = "EXIT"
    assert funding_ledger(context, proposed)["status"] == "balanced"


@pytest.mark.parametrize("value", [float('nan'), float('inf'), -1, 101, True, None])
def test_invalid_target_is_rejected(value):
    value_rows = proposal()
    value_rows["asset_class_targets"][0]["target_pct"] = value
    assert validate_stage(value_rows, {"required_schema": {"asset_class_targets": [{}]}})


def test_point_in_time_facts_and_unknown_references():
    assert normalize_facts([fact()], packet())[0]["evidence_status"] == "source_matched"
    for change in ({"published_at": "2026-08-12"}, {"observed_at": "2026-08-12"}, {"source_ids": ["invented"]}, {"currency": None}, {"value": 99}, {"source_excerpt": "Invented value"}):
        assert normalize_facts([{**fact(), **change}], packet())[0]["evidence_status"] == "needs_verification"


def test_excerpt_match_does_not_verify_a_relabelled_fact():
    from backend.portfolio_evidence import apply_fact_checks, fact_is_supported
    wrong = normalize_facts([{**fact(), "metric": "bond yield", "benchmark": "Australian government bond"}], packet())[0]
    assert not fact_is_supported(wrong)
    checked = apply_fact_checks([wrong], [{"fact_id": "f1", "checks": {
        key: "unsupported" if key in {"metric", "benchmark"} else "supported"
        for key in ("metric", "value", "unit", "benchmark", "currency", "observed_at", "published_at", "vintage")},
        "reason": "The source reports GDP, not a bond yield."}], packet())
    assert not fact_is_supported(checked[0])
    assert checked[0]["claim_status"] == "unsupported"


def test_unknown_weights_survive_the_entire_input_path():
    context = snapshot()
    context["asset_classes"].append({"asset_class": "unpriced", "portfolio_pct": None})
    compact = memo._compact_snapshot(context)
    assert compact["asset_classes"][-1]["portfolio_pct"] is None
    assert compact["weight_diagnostics"]["asset_class_total_pct"] is None
    assert compact["weight_diagnostics"]["unresolved_asset_class_count"] == 1
    assert any(row["asset_class"] == "unpriced" and row["current_pct"] is None for row in memo._current_asset_class_rows(compact))
    assert funding_ledger(compact, proposal())["status"] == "unresolved"
    context["asset_classes"] = [{"asset_class": "equity", "portfolio_pct": 0.5}]
    assert memo._compact_snapshot(context)["asset_classes"][0]["portfolio_pct"] == 0.5
    context["asset_classes"] = []
    context["positions"] = [{"ticker": "ASX:ABC", "asset_class": "unpriced"}]
    compact = memo._compact_snapshot(context)
    assert compact["asset_classes"][0]["portfolio_pct"] is None
    assert funding_ledger(compact, proposal())["status"] == "unresolved"


def test_health_detects_postprocessing_failure_and_missing_required_lane():
    artifact = {"portfolio_snapshot": snapshot(), "macro_positioning": proposal(),
        "evidence_brief": {"evidence_status": "complete", "asset_class_coverage_quality": {"status": "ok"}},
        "stage_receipts": [{"stage": "research", "input_hash": "x", "status": "complete"}],
        "expected_evidence_lanes": ["macro", "sector"],
        "evidence_runs": [{"label": "macro", "error": "Post-processing failed"}]}
    health = analysis_health(artifact)
    assert health["status"] == "incomplete"
    assert any("Post-processing" in issue["detail"] for issue in health["issues"])
    assert any("sector" in issue["detail"] for issue in health["issues"])


@pytest.mark.parametrize("coverage_status", ["unassessed", "failed_all_none"])
def test_coverage_metadata_gap_keeps_completed_memo_with_limitations(tmp_path, coverage_status):
    from backend.jobs.executor import _analysis_job_output_error
    artifact = {"pipeline_status": "complete", "portfolio_snapshot": snapshot(), "macro_positioning": proposal(),
        "analyst_memo_markdown": "# Portfolio memo\n\nThe recorded allocation and research remain available.",
        "evidence_brief": {"evidence_status": "complete", "facts": [fact()],
            "asset_class_coverage": [{"asset_class": "equity", "stance": "UNASSESSED", "fact_ids": [], "source_ids": []}],
            "asset_class_coverage_quality": {"status": coverage_status},
            "research_limitations": ["The exact market observation remains unverified."]},
        "stage_receipts": [{"stage": "memo", "input_hash": "memo", "status": "complete"}]}
    before = copy.deepcopy(artifact)
    health = analysis_health(artifact)
    assert health["status"] == "complete"
    assert health["label"] == "Analysis complete with limitations"
    assert health["decision_status"] == "needs_review"
    assert {row["stage"] for row in health["warnings"]} == {"research", "coverage"}
    assert artifact == before
    path = tmp_path / "memo.json"
    path.write_text(json.dumps(artifact))
    assert _analysis_job_output_error(path, {"job_type": "portfolio_positioning"}) == ""


def test_job_error_does_not_present_research_warnings_as_blocking_failures(tmp_path):
    from backend.jobs.executor import _analysis_job_output_error
    artifact = {"portfolio_snapshot": snapshot(), "macro_positioning": {},
        "evidence_brief": {"evidence_status": "complete", "asset_class_coverage_quality": {"status": "unassessed"},
            "research_limitations": ["Supplementary market question remains unanswered."]},
        "stage_receipts": [{"stage": "optional search", "status": "failed", "optional": True, "error": "Supplementary search failed"},
                           {"stage": "research", "status": "complete"}]}
    path = tmp_path / "incomplete.json"
    path.write_text(json.dumps(artifact))
    error = _analysis_job_output_error(path, {"job_type": "portfolio_positioning"})
    assert "allocation: No final weight specified" in error
    assert "coverage" not in error
    assert "Supplementary" not in error


@pytest.mark.asyncio
async def test_crash_preserves_accessible_partial_artifact(tmp_path, monkeypatch):
    async def crash(args):
        runtime = CURRENT_RUNTIME.get()
        runtime.update_partial(portfolio_snapshot=snapshot(), portfolio_context=snapshot())
        await runtime.research("research", {"query": "test"}, AsyncMock(return_value={"research_summary": "Retained evidence"}))
        raise RuntimeError("Post-research failure")
    monkeypatch.setattr(memo, "_run_pipeline", crash)
    output = tmp_path / "crashed.json"
    assert await memo._async_main(argparse.Namespace(dump_json=str(output), resume_checkpoint=None)) == 1
    artifact = json.loads(output.read_text())
    assert artifact["pipeline_error"] == "RuntimeError: Post-research failure"
    assert artifact["portfolio_snapshot"] == snapshot()
    assert artifact["retained_research"]
    assert analysis_health(artifact)["status"] == "incomplete"
    from backend.routers import runs
    monkeypatch.setattr(runs, "_resolve_portfolio_positioning_artifact_path", lambda name: output)
    response = await runs.get_portfolio_positioning_run(output.name)
    assert response["can_resume"] is True


@pytest.mark.parametrize("start,end", [("2020-01-01", "2020-02-01"), ("2030-01-01", "2030-02-01")])
def test_performance_cannot_use_predecision_or_future_returns(start, end):
    decision = build_decision(snapshot(), proposal(), {})
    returns = [{"asset_class": asset, "total_return_pct": 10, "currency": "AUD", "transaction_cost_bps": 0,
        "from": start, "to": end, "source_url": "https://example.org"} for asset in ("equity", "cash")]
    assert shadow_returns(decision, returns, as_of="2026-09-15")["status"] == "incomplete"


def test_drawdown_must_match_reported_period_and_endpoint():
    decision = build_decision(snapshot(), proposal(), {})
    returns = [{"asset_class": asset, "total_return_pct": 10, "currency": "AUD", "transaction_cost_bps": 0,
        "from": "2026-08-11", "to": "2026-09-11", "source_url": "https://example.org",
        "cumulative_total_returns": [{"date": "1999-01-01", "return_pct": 0}, {"date": "1999-02-01", "return_pct": -50}]}
        for asset in ("equity", "cash")]
    assert shadow_returns(decision, returns, as_of="2026-09-15")["drawdown"]["status"] == "unassessed"
    for row in returns:
        row["cumulative_total_returns"][0]["date"] = row["from"]
        row["cumulative_total_returns"][1]["date"] = row["to"]
    assert shadow_returns(decision, returns, as_of="2026-09-15")["drawdown"]["status"] == "unassessed"


@pytest.mark.parametrize("key,value", [("horizon_months", -12), ("max_drawdown_pct", -5), ("liquidity_min_pct", -10), ("base_currency", "unknown")])
def test_invalid_mandate_is_reported(key, value):
    context = snapshot()
    context["mandate"][key] = value
    decision = build_decision(context, proposal(), {})
    assert decision["mandate_issues"]
    assert decision["status"] == "needs_review"


def test_conditions_select_latest_available_revision_regardless_of_order():
    condition = {"metric": "inflation", "benchmark": "CPI", "unit": "pct", "threshold": 3, "operator": "gte", "max_age_days": 30}
    old = {"metric": "inflation", "benchmark": "CPI", "unit": "pct", "observed_at": "2026-08-01", "published_at": "2026-08-02", "value": 2, "source_url": "https://example.org/first"}
    revised = {**old, "published_at": "2026-08-10", "value": 4}
    for observations in ([old, revised], [revised, old]):
        assert evaluate_conditions([condition], observations, "2026-08-11")[0]["status"] == "triggered"
        assert evaluate_conditions([condition], observations, "2026-08-05")[0]["status"] == "not_triggered"


def test_missing_trade_details_are_not_external_research_questions():
    decision = build_decision(snapshot(), proposal(), {})
    decision["funding"]["rows"][0].update(implementation={"instrument_type": "specific ETF"}, rationale="Expected earnings exceed priced expectations", contrary_evidence=["Margin compression"])
    questions = memo._trade_research_questions(decision)
    assert questions == []


def test_source_review_is_bound_to_the_claim_and_macro_is_not_market_pricing():
    from backend.portfolio_evidence import apply_fact_checks, fact_is_supported, FACT_FIELDS
    reviewed = apply_fact_checks([fact()], [{"fact_id": "f1", "checks": {key: "supported" for key in FACT_FIELDS}, "reason": "Source fields checked"}], packet())[0]
    assert fact_is_supported(reviewed)
    assert not fact_is_supported({**reviewed, "benchmark": "Unrelated bond"})
    proposed = proposal()
    proposed["asset_class_targets"][0].update(fact_ids=["f1"], thesis_conviction="STRONG",
        market_pricing={"benchmark": reviewed["benchmark"], "observed_expectation": "GDP is a market price", "fact_ids": ["f1"]},
        investment_case={key: "Unknown" for key in ("why_better_than_hold", "why_better_than_cash", "downside", "cost_assumptions", "horizon_months")},
        alternatives=[{}], contrary_evidence=[{}])
    decision = build_decision(snapshot(), proposed, {"facts": [reviewed], "evidence_status": "complete"})
    row = decision["funding"]["rows"][0]
    assert row["conviction"] == "STRONG"
    assert row["sizing_confidence"] == "UNASSESSED"
    assert any("Market-implied" in item for item in row["open_questions"])
    assert any("missing" in item for item in row["open_questions"])


def test_drawdown_review_is_bound_to_allocation_and_can_identify_a_breach():
    context, proposed = snapshot(), proposal()
    decision = build_decision(context, proposed, {})
    context["risk_assessment"] = {"allocation_hash": decision["allocation_hash"], "estimated_max_drawdown_pct": 30,
        "as_of": "2026-08-10", "method": "External portfolio stress model", "source_url": "https://example.org/risk-report"}
    checked = build_decision(context, proposed, {})
    assert next(row for row in checked["mandate_checks"] if row["constraint"] == "max_drawdown_pct")["status"] == "breach"
    context["risk_assessment"]["estimated_max_drawdown_pct"] = 15
    checked = build_decision(context, proposed, {})
    assert next(row for row in checked["mandate_checks"] if row["constraint"] == "max_drawdown_pct")["status"] == "compliant"
    changed = build_decision(context, proposal(70), {})
    assert next(row for row in changed["mandate_checks"] if row["constraint"] == "max_drawdown_pct")["status"] == "unassessed"


def test_custom_benchmark_does_not_change_portfolio_funding():
    context = snapshot()
    context["mandate"]["benchmark"] = "ASX200"
    decision = build_decision(context, proposal(), {})
    returns = [{"asset_class": asset, "total_return_pct": value, "currency": "AUD", "transaction_cost_bps": 0,
        "from": "2026-08-11", "to": "2026-09-11", "source_url": "https://example.org"}
        for asset, value in (("equity", 10), ("cash", 1), ("ASX200", 4))]
    result = shadow_returns(decision, returns, as_of="2026-09-15")
    assert result["status"] == "measured"
    assert result["benchmark"]["return_pct"] == 4
    assert result["benchmark"]["excess_return_pp"] == pytest.approx(2.4)
    exposures = {asset: {"sensitivities": {"equity_pct": sensitivity}, "currency": "AUD", "annual_carry_pct": 0,
        "transaction_cost_bps": 0, "basis": "Test scenario", "source": "Test source"} for asset, sensitivity in (("equity", 1), ("cash", 0), ("ASX200", 0.8))}
    comparison = scenario_comparison(decision, [{"name": "Test", "shocks": {"equity_pct": -10}, "horizon_months": 12}], exposures)[0]
    assert comparison["proposed_return_pct"] == -6
    assert comparison["benchmark"]["return_pct"] == -8


def test_merge_preserves_all_research_and_resolves_colliding_fact_ids():
    first = {"facts": [fact()], "source_packet": {**packet(), "research": [{"text": "A" * 5000}]}, "prompt_audit": {"secret_instruction": "ignore"}}
    second = {"facts": [{**fact(), "value": 4}], "source_packet": {**packet(), "research": [{"text": "B" * 5000}]}}
    merged = merge_briefs([first, second])
    assert len(merged["source_packet"]["research"]) == 2
    assert len({row["id"] for row in merged["facts"]}) == 2
    assert len(json.dumps(merged)) > 10000
    assert "prompt_audit" not in json.dumps(business_data(first))
    assert merged["evidence_status"] == "incomplete"


def test_reconciliation_keeps_fact_ids_stable_after_source_review():
    from backend.portfolio_evidence import apply_fact_checks, FACT_FIELDS
    first = merge_briefs([{"facts": normalize_facts([fact()], packet()), "source_packet": packet()}])
    fact_id = first["facts"][0]["id"]
    first["facts"] = apply_fact_checks(first["facts"], [{"fact_id": fact_id, "checks": {key: "supported" for key in FACT_FIELDS}, "reason": "Reviewed"}], first["source_packet"])
    second = merge_briefs([first])
    assert second["facts"][0]["id"] == fact_id


@pytest.mark.asyncio
async def test_recovery_endpoint_accepts_crashed_partial_run(tmp_path, monkeypatch):
    import asyncio
    import httpx
    from fastapi import FastAPI
    from backend.routers import analysis_jobs
    monkeypatch.setattr(analysis_jobs, "_portfolio_preflight", AsyncMock(return_value={"status": "ready"}))
    from backend.jobs import runs as job_runs
    output = tmp_path / "partial.json"
    runtime = PortfolioRuntime(output.with_suffix(".checkpoint.json"), artifact_path=output)
    runtime.update_partial(portfolio_snapshot=snapshot(), portfolio_context=snapshot(), query="Frozen query", pipeline_status="failed", pipeline_error="Test crash")
    monkeypatch.setattr(job_runs, "_resolve_portfolio_positioning_artifact_path", lambda name: output)
    monkeypatch.setattr(analysis_jobs, "_ensure_analysis_job_dirs", lambda: None)
    monkeypatch.setattr(analysis_jobs, "_persist_job_record", lambda job: None)
    monkeypatch.setattr(analysis_jobs, "PORTFOLIO_POSITIONING_OUTPUTS_DIR", tmp_path)
    context_path = tmp_path / "context.json"
    def store(context, **kwargs):
        context_path.write_text(json.dumps(context))
        return context_path
    monkeypatch.setattr(analysis_jobs, "_store_portfolio_context_for_job", store)
    worker = AsyncMock()
    monkeypatch.setattr(analysis_jobs, "_run_analysis_job", worker)
    app = FastAPI()
    app.include_router(analysis_jobs.router)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/api/analysis-jobs", json={"job_type": "portfolio_positioning", "resume_portfolio_run_id": output.name})
    await asyncio.sleep(0)
    assert response.status_code == 202, response.text
    command = worker.call_args.kwargs["command"]
    assert command[command.index("--resume-checkpoint") + 1] == str(output.with_suffix(".checkpoint.json"))
    assert json.loads(context_path.read_text())["asset_classes"] == snapshot()["asset_classes"]
    analysis_jobs.ANALYSIS_JOBS.pop(response.json()["job_id"], None)


def test_watch_without_evidence_is_unassessed():
    result = memo._normalize_evidence_asset_coverage({"asset_class_coverage": [{"asset_class": "equity", "stance": "WATCH", "evidence_strength": "HIGH", "fact_ids": ["made_up"], "evidence_summary": "Positive"}]}, asset_class_vocabulary=[])
    assert result["asset_class_coverage_quality"]["non_none_row_count"] == 0


def test_regime_is_not_rewritten_from_decimal_substrings():
    assessment = {"best_fit": "Q1", "why_now": "Growth accelerated to 3.0%, up 0.2 percentage points"}
    assert memo._sharpen_quadrant_assessment({"quadrant_assessment": assessment}) == assessment


@pytest.mark.asyncio
async def test_402_receipt_is_not_retried_and_is_preserved(tmp_path):
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    client = AsyncMock(return_value={"error": "Insufficient credits", "error_type": "http_error", "error_status": 402, "content": ""})
    result = await runtime.query(client, 'model', [{"role": "user", "content": json.dumps({"task": "test", "required_schema": {"answer": "string"}})}], parser=memo._extract_json_object, validator=validate_stage)
    assert result["stage_status"] == "failed"
    assert client.await_count == 1
    assert runtime.receipts[-1]["error_status"] == 402
    assert not json.loads((tmp_path / "checkpoint.json").read_text())["stage_cache"]


@pytest.mark.asyncio
async def test_parse_repair_and_checkpoint_reuse(tmp_path):
    path = tmp_path / "checkpoint.json"
    runtime = PortfolioRuntime(path)
    client = AsyncMock(side_effect=[{"content": "broken", "finish_reason": "length"}, {"content": '{"answer": "fixed"}'}])
    messages = [{"role": "user", "content": json.dumps({"task": "test", "required_schema": {"answer": "string"}})}]
    result = await runtime.query(client, 'model', messages, parser=memo._extract_json_object, validator=validate_stage, max_tokens=100)
    assert result["stage_status"] == "complete"
    assert "max_tokens" not in client.call_args.kwargs
    reused = PortfolioRuntime(tmp_path / "new.json", path)
    unused = AsyncMock(side_effect=AssertionError("Must not query completed stage"))
    await reused.query(unused, 'model', messages, parser=memo._extract_json_object, validator=validate_stage, max_tokens=100)
    assert reused.receipts[-1]["reused"]
    assert unused.await_count == 0


@pytest.mark.asyncio
async def test_blind_prior_does_not_receive_holdings(monkeypatch):
    prompts = []
    async def query(model, messages, **kwargs):
        prompts.append(json.loads(messages[0]["content"]))
        return {"content": "{}"}
    monkeypatch.setattr(memo, "_query_stage", query)
    await memo._run_chairman(query="Macro view", mode="deep", evidence_brief={}, asset_class_vocabulary=[], snapshot=snapshot(), lane_strategy="blind_macro_prior")
    assert prompts[0]["portfolio_context"] == {}
    assert "100000" not in json.dumps(prompts)


def test_commentary_cannot_rewrite_allocations_or_confidence():
    structured = {"asset_class_targets": [{"asset_class": "equity", "target_pct": 60, "conviction": "UNASSESSED"}]}
    result = memo._apply_allocator_commentary(structured=structured, commentary={"asset_comments": [{"asset_class": "equity", "commentary": "Notes", "target_pct": 99, "conviction": "STRONG"}]})
    assert result["asset_class_targets"][0]["target_pct"] == 60
    assert result["asset_class_targets"][0]["conviction"] == "UNASSESSED"


def test_explicit_scenario_math_and_missing_inputs():
    decision = build_decision(snapshot(), proposal(), {})
    exposures = {asset: {"sensitivities": {"equity_pct": beta}, "annual_carry_pct": 2, "transaction_cost_bps": 10, "currency": "AUD", "source": "analyst estimate", "basis": "documented assumption"} for asset, beta in (("equity", 1), ("cash", 0))}
    scenario = [{"name": "Equity decline", "horizon_months": 12, "shocks": {"equity_pct": -10}}]
    result = scenario_comparison(decision, scenario, exposures)[0]
    assert result["hold_return_pct"] == pytest.approx(-6)
    assert result["proposed_return_pct"] == pytest.approx(-4.04)
    exposures["equity"]["sensitivities"] = {}
    assert scenario_comparison(decision, scenario, exposures)[0]["proposed_return_pct"] is None


def test_conditions_require_correct_benchmark_dates_and_source():
    condition = {"id": "c1", "metric": "oil", "benchmark": "Brent", "unit": "USD/bbl", "operator": "gte", "threshold": 100, "max_age_days": 7}
    observation = {"metric": "oil", "benchmark": "Brent", "unit": "USD/bbl", "value": 110, "observed_at": "2026-08-10", "published_at": "2026-08-10", "source_url": "https://example.org"}
    assert evaluate_conditions([condition], [observation], "2026-08-11")[0]["status"] == "triggered"
    for changes in ({"benchmark": "WTI"}, {"observed_at": "2026-08-12"}, {"published_at": "2026-08-12"}, {"observed_at": "2026-08-01"}):
        assert evaluate_conditions([condition], [{**observation, **changes}], "2026-08-11")[0]["status"] == "unassessed"


def test_shadow_returns_costs_alignment_and_calibration():
    decision = build_decision(snapshot(), proposal(), {})
    returns = [{"asset_class": asset, "total_return_pct": value, "transaction_cost_bps": 10, "currency": "AUD", "from": "2026-08-11", "to": "2026-09-11", "source_url": "https://example.org"} for asset, value in (("equity", -10), ("cash", 1))]
    result = shadow_returns(decision, returns)
    assert result["hold_return_pct"] == pytest.approx(-7.8)
    assert result["proposal_return_pct"] == pytest.approx(-5.64)
    assert result["drawdown"]["status"] == "unassessed"
    returns[0]["currency"] = "USD"
    assert shadow_returns(decision, returns)["status"] == "incomplete"
    assert forecast_calibration([], [], "2026-09-11")["mean_brier_score"] is None


def test_measured_drawdown_and_matured_forecast():
    decision = build_decision(snapshot(), proposal(), {})
    returns = [{"asset_class": asset, "currency": "AUD", "transaction_cost_bps": 0, "source_url": "https://example.org",
        "from": "2026-08-11", "to": "2026-09-11", "total_return_pct": change,
        "cumulative_total_returns": [{"date": "2026-08-11", "return_pct": 0}, {"date": "2026-09-11", "return_pct": change}]}
        for asset, change in (("equity", -10), ("cash", 0))]
    result = shadow_returns(decision, returns)
    assert result["drawdown"]["hold_max_drawdown_pct"] == pytest.approx(-8)
    assert result["drawdown"]["proposal_max_drawdown_pct"] == pytest.approx(-6)
    forecast = {"id": "inflation", "metric": "inflation", "benchmark": "test CPI", "unit": "pct", "operator": "gt", "threshold": 3,
        "probability": 0.7, "deadline": "2026-09-11", "max_age_days": 10}
    observation = {"metric": "inflation", "benchmark": "test CPI", "unit": "pct", "value": 4, "source_url": "https://example.org",
        "published_at": "2026-09-10", "observed_at": "2026-09-10"}
    assert forecast_calibration([forecast], [observation], "2026-09-12")["mean_brier_score"] == pytest.approx(0.09)
    assert forecast_calibration([forecast], [observation], "2026-09-01")["scored_count"] == 0


@pytest.mark.asyncio
async def test_failed_portfolio_job_still_exposes_saved_research(tmp_path, monkeypatch):
    from backend.routers import analysis_jobs
    job = {"job_id": "partial", "run_id": "portfolio.json", "status": "failed", "request": {"job_type": "portfolio_positioning"}}
    monkeypatch.setitem(analysis_jobs.ANALYSIS_JOBS, "partial", job)
    monkeypatch.setattr(analysis_jobs, "get_portfolio_positioning_run", AsyncMock(return_value={"id": "portfolio.json", "analysis_health": {"status": "incomplete"}}))
    result = await analysis_jobs.get_analysis_job_result("partial")
    assert result["run"]["analysis_health"]["status"] == "incomplete"


def test_output_validator_rejects_false_success_without_rewriting_legacy_status(tmp_path):
    from backend.jobs.executor import _analysis_job_output_error
    path = tmp_path / "portfolio.json"
    path.write_text(json.dumps({"portfolio_snapshot": snapshot(), "macro_positioning": proposal()}))
    assert "incomplete" in _analysis_job_output_error(path, {"job_type": "portfolio_positioning"}).lower()
    assert _analysis_job_output_error(path, {"job_type": "portfolio_positioning"}, preserve_legacy_status=True) == ""


def test_historical_run_is_flagged_without_modifying_it():
    artifact = {"portfolio_snapshot": snapshot(), "macro_positioning": proposal(), "evidence_brief": {"asset_class_coverage_quality": {"status": "failed_all_none"}}, "portfolio_memo_ensemble": {"consensus": {"mode": "fallback_first_valid"}}}
    before = copy.deepcopy(artifact)
    assert analysis_health(artifact)["status"] == "historical"
    assert analysis_health(artifact)["warnings"]
    assert artifact == before


@pytest.mark.asyncio
async def test_review_api_preserves_original_and_stores_inputs(tmp_path, monkeypatch):
    from backend.routers import runs
    path = tmp_path / "portfolio.json"
    original = json.dumps({"portfolio_snapshot": snapshot(), "macro_positioning": proposal()})
    path.write_text(original)
    monkeypatch.setattr(runs, "_resolve_portfolio_positioning_artifact_path", lambda name: path)
    monkeypatch.setattr(runs, "_ensure_system_enabled", lambda: None)
    response = await runs.review_portfolio_positioning_run(path.name, runs.PortfolioReviewRequest(mandate=snapshot()["mandate"]))
    assert response["decision"]["funding"]["status"] == "balanced"
    assert path.read_text() == original
    assert len((await runs.list_portfolio_reviews(path.name))["reviews"]) == 1


@pytest.mark.asyncio
async def test_stage_details_are_available_without_expanding_run_payload(tmp_path, monkeypatch):
    from backend.routers import runs
    from fastapi import HTTPException
    path = tmp_path / "portfolio.json"
    record = {"request_messages": [{"role": "user", "content": "test"}], "raw_response": {"error_status": 402}}
    path.write_text(json.dumps({"stage_receipts": [record]}))
    monkeypatch.setattr(runs, "_resolve_portfolio_positioning_artifact_path", lambda name: path)
    assert (await runs.get_portfolio_stage_record(path.name, 0))["record"] == record
    with pytest.raises(HTTPException) as exc:
        await runs.get_portfolio_stage_record(path.name, -1)
    assert exc.value.status_code == 404


def test_macro_retrieval_does_not_apply_company_prompt_or_source_ranking(monkeypatch):
    from backend.research.providers.perplexity import PerplexityResearchProvider
    provider = PerplexityResearchProvider()
    prompt = provider._build_prompt("GDP", None, "deep", 12, research_profile="macro")
    assert "management/governance" not in prompt
    assert "publication date" in prompt
    monkeypatch.setattr(provider, "_score_candidate", lambda **kw: pytest.fail("Company ranking must not run"))
    result = provider._candidates_to_results([{"url": "https://example.org/gdp", "title": "GDP", "snippet": "GDP data"}], 12, research_profile="macro")
    assert len(result) == 1


def test_company_research_point_in_time_link_and_event_dedup(tmp_path):
    from backend.portfolio_intelligence import link_company_evidence
    from backend.scenario_router.lab_scribe import LabScribe
    path = tmp_path / "company.json"
    path.write_text(json.dumps({"updated_at": "2026-08-01", "structured_data": {"ticker": "ASX:ABC", "thesis": "Example"}}))
    events = tmp_path / "events" / "by_run" / LabScribe._safe_key(path.name)
    events.mkdir(parents=True)
    event = {"saved_at_utc": "2026-08-09", "event": {"event_id": "123"}, "announcement_facts": {"catalyst": "same action"}}
    (events / "a.json").write_text(json.dumps(event))
    (events / "latest.json").write_text(json.dumps(event))
    (events / "future.json").write_text(json.dumps({**event, "saved_at_utc": "2026-09-01", "event": {"event_id": "future"}}))
    context = {"positions": [{"ticker": "ASX:ABC", "council_run_id": path.name, "asset_class": "equity", "portfolio_pct": 10}]}
    result = link_company_evidence(context, "2026-08-11", resolver=lambda name: path, events_dir=tmp_path / "events")
    assert result[0]["status"] == "linked"
    assert len(result[0]["announcements"]) == 1
    assert result[0]["artifact_hash"]


def test_company_context_includes_unclassified_filings_and_older_baselines(tmp_path):
    from backend.portfolio_intelligence import link_company_evidence
    ticker_dir = tmp_path / "ASX:ABC"
    ticker_dir.mkdir()
    for event_id, status in (("failed", "processing_error"), ("older_baseline", "ok")):
        (ticker_dir / f"{event_id}.json").write_text(json.dumps({"saved_at_utc": "2026-08-09",
            "event": {"event_id": event_id, "ticker": "ASX:ABC"}, "status": status,
            "baseline_run": {"run_id": "previous.json"}}))
    context = {"positions": [{"ticker": "ASX:ABC"}]}
    record = link_company_evidence(context, "2026-08-11", events_dir=tmp_path)[0]
    assert len(record["announcements"]) == 2
    assert any("processing_error" in issue for issue in record["coverage_issues"])


@pytest.mark.asyncio
async def test_auto_company_link_uses_exact_ticker_and_known_vintage():
    from backend.portfolio_intelligence import attach_company_runs
    data = {"positions": [{"ticker": "ASX:ABC"}, {"ticker": "ABC"}, {"ticker": "ASX:XYZ", "council_run_id": "explicit.json"}]}
    listing = AsyncMock(return_value={"runs": [
        {"ticker": "ASX:ABC", "analysis_date": "2026-08-01", "id": "valid.json"},
        {"ticker": "ASX:ABC", "analysis_date": "2026-09-01", "id": "future.json"},
        {"ticker": "NYSE:ABC", "analysis_date": "2026-08-10", "id": "wrong_exchange.json"},
    ]})
    await attach_company_runs(data, "2026-08-11", listing=listing)
    assert data["positions"][0]["council_run_id"] == "valid.json"
    assert "council_run_id" not in data["positions"][1]
    assert data["positions"][2]["council_run_id"] == "explicit.json"
    assert listing.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("defect", [None, "missing_review_field", "missing_details", "supplementary_search_failure"])
@pytest.mark.parametrize("workflow_version", [1, 2])
async def test_full_pipeline_offline_and_recovery(monkeypatch, tmp_path, defect, workflow_version):
    monkeypatch.setattr(memo, "FundingGuard", lambda: None)
    original_runtime = memo.PortfolioRuntime
    def runtime(*args, **kwargs):
        result = original_runtime(*args, **kwargs)
        if not (len(args) > 1 and args[1]) and not kwargs.get("resume"):
            result.workflow_version = workflow_version
        return result
    monkeypatch.setattr(memo, "PortfolioRuntime", runtime)
    research = {"research_summary": "GDP growth was 3.1 percent.", "results": [{"title": "GDP release", "url": "https://example.org/gdp", "content": "GDP growth was 3.1 percent.", "published_at": "2026-08-10"}]}
    monkeypatch.setattr(memo, "_fetch_xai_macro_environment_summary", AsyncMock(return_value=research))
    async def retrieve(*args, **kwargs):
        if kwargs.get("question") == "What is the current earnings yield of equities?":
            return {"error": "Supplementary provider unavailable", "results": []}
        return {**copy.deepcopy(research), "provider": "parallel"}
    monkeypatch.setattr(memo.ParallelSourceProvider, "gather", AsyncMock(side_effect=retrieve))
    monkeypatch.setattr(memo, "DEFAULT_DEEP_EVIDENCE_RUNS", 3)
    monkeypatch.setattr(memo, "DEFAULT_DEEP_ENSEMBLE_RUNS", 3)
    prompts = []
    async def client(model, messages, **kwargs):
        assert "max_tokens" not in kwargs
        prompt = json.loads(messages[0]["content"])
        prompts.append(prompt)
        schema = prompt["required_schema"]
        result = {key: [] if isinstance(value, list) else {} if isinstance(value, dict) else "Offline fixture" for key, value in schema.items()}
        evidence = prompt.get("evidence_brief") or prompt.get("evidence") or {}
        facts = evidence.get("facts") or []
        if "facts" in schema:
            source = prompt["source_packet"]["sources"][0]
            facts = [{**fact(), "source_ids": [source["id"]]}]
            result["facts"] = facts
        if "questions" in schema and defect == "supplementary_search_failure":
            result["questions"] = [{"question": "What is the current earnings yield of equities?", "kind": "market_fact",
                "status": "unanswered", "asset_classes": ["equity"], "material_reason": "Valuation could change the proposed trim",
                "reuse_assessment": "GDP does not establish the earnings yield", "existing_fact_ids": []}]
        if "asset_class_coverage" in schema:
            result["asset_class_coverage"] = [{"asset_class": "equity", "evidence_strength": "LOW", "stance": "WATCH", "fact_ids": [row["id"] for row in facts], "evidence_summary": "GDP release"}]
        if "fact_checks" in schema:
            result["fact_checks"] = [{"fact_id": row["id"], "checks": {key: "unresolved" for key in schema["fact_checks"][0]["checks"]}, "reason": "Fixture source does not establish every field"} for row in facts]
            if defect == "missing_review_field":
                result["fact_checks"][0]["checks"].pop("currency")
        if "asset_class_targets" in schema:
            result.update(proposal())
            for row in result["asset_class_targets"]:
                row.update(fact_ids=[item["id"] for item in facts], thesis_conviction="STRONG", rationale="Offline test only")
        if "allocation_details" in schema:
            def unknown(template):
                if isinstance(template, dict):
                    return {key: unknown(value) for key, value in template.items()}
                return [] if isinstance(template, list) else "unknown"
            result["allocation_details"] = [{**unknown(schema["allocation_details"][0]), "asset_class": row["asset_class"]}
                                            for row in prompt["assigned_allocations"]]
            if defect == "missing_details":
                result["allocation_details"][0].pop("investment_case")
        return {"content": json.dumps(result), "id": f"offline-{len(prompts)}", "usage": {"total_tokens": 0}}
    monkeypatch.setattr(memo, "query_model", client)
    context_path = tmp_path / "context.json"
    context_path.write_text(json.dumps(snapshot()))
    output = tmp_path / "run.json"
    args = argparse.Namespace(portfolio_context_file=str(context_path), query="Test macro", mode="deep", dump_json=str(output), run_label="Offline verification", resume_checkpoint=None)
    assert await memo._async_main(args) == 0
    artifact = json.loads(output.read_text())
    assert artifact["stage_receipts"]
    assert artifact["analysis_health"]["status"] == "complete", artifact["analysis_health"]
    assert artifact["structured_data"]["decision"]["status"] == "needs_review"
    assert artifact["targeted_research"]["status"] == ("with_limitations" if defect == "supplementary_search_failure" else "not_needed")
    assert len(artifact["analyst_memo_markdown"]) > 100
    if defect:
        assert artifact["analysis_health"]["warnings"]
        assert artifact["analysis_health"]["label"] == "Analysis complete with limitations"
        from backend.jobs.executor import _analysis_job_output_error
        assert _analysis_job_output_error(output, {"job_type": "portfolio_positioning"}) == ""
    blind = [prompt for prompt in prompts if prompt.get("lane_strategy") == "blind_macro_prior"]
    assert len(blind) == 1 and blind[0]["portfolio_context"] == {}
    from collections import Counter
    roles = Counter(prompt["lane_strategy"] for prompt in prompts if prompt.get("lane_strategy"))
    repeats = 3 if workflow_version == 1 else 1
    assert roles == {"blind_macro_prior": 1, "portfolio_aware_allocator": repeats,
                     "exposure_equivalence_reviewer": repeats, "defensive_regime_reviewer": repeats}
    if workflow_version == 2:
        assert sum(prompt["task"].startswith("Act as the portfolio-positioning judge") for prompt in prompts) == 1
        assert sum(prompt["task"].startswith("Resolve the complementary allocator") for prompt in prompts) == 1
        assert sum(prompt["task"] == "Explain the recorded portfolio decision without changing it" for prompt in prompts) == 1
        assert all(prompt["task"].startswith("Final portfolio investment case") for prompt in prompts if "allocation_details" in prompt["required_schema"])
    assert all("prompt_audit" not in json.dumps(prompt) for prompt in prompts)
    context_path.write_text(json.dumps(artifact["portfolio_snapshot"]))
    args.resume_checkpoint = str(output.with_suffix(".checkpoint.json"))
    args.dump_json = str(tmp_path / "recovered.json")
    before = len(prompts)
    assert await memo._async_main(args) == 0
    recovered = json.loads(Path(args.dump_json).read_text())
    assert len(prompts) == before
    assert all(receipt["reused"] for receipt in recovered["stage_receipts"])
    if defect:
        assert recovered["analysis_health"]["warnings"]
