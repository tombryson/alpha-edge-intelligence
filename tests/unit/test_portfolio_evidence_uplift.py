import asyncio
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from backend.portfolio_decisions import evaluate_conditions, funding_ledger
from backend.portfolio_documents import pdf_context
from backend.portfolio_evidence import (
    FACT_FIELDS, apply_fact_checks, availability, fact_observation_is_supported, normalize_facts,
)
from backend.portfolio_judgment import apply_claim_patches, calculation_issues, detail_basis, implementation_comparison
from backend.portfolio_research import complete_component_plan, coverage, restore_phase_research
from backend.portfolio_requests import observation_brief, expand_observations
from backend.portfolio_runtime import CURRENT_RUNTIME, PortfolioRuntime
from backend.portfolio_sources import hydrate_citations
from backend.portfolio_tasks import evidence_for_decisions


def source_case():
    packet = {"as_of": "2026-09-21T02:00:00Z", "sources": [{"id": "s", "url": "https://example.test/report.pdf", "excerpt": "Annual 2023: Brent 82.6. August 2026: Brent 90.9.", "published_at": "2026-09-01"}]}
    fact = {"id": "old", "kind": "market_price", "metric": "Brent", "value": 82.6, "unit": "USD/bbl", "currency": "USD",
        "benchmark": "Brent", "observed_at": "2026-08-01", "published_at": "2026-09-01", "vintage": "September 2026",
        "source_ids": ["s"], "source_excerpt": packet["sources"][0]["excerpt"]}
    return packet, fact


def check(identifier, **kwargs):
    return {"fact_id": identifier, "checks": {key: "supported" for key in FACT_FIELDS}, "reason": "Exact source supports this observation", **kwargs}


def test_forecast_is_not_an_observed_outcome_and_naive_clock_is_not_utc():
    packet, fact = source_case()
    fact.update(kind="forecast", observed_at=None, published_at="2026-09-21T09:03:00",
                reference_period="2026 calendar year")
    normalized = normalize_facts([fact], packet)[0]
    assert not any("observed_at" in issue or "after" in issue for issue in normalized["verification_issues"])
    assert normalized["availability_status"] == "timezone_unknown"
    assert availability("2026-09-22T09:00:00Z", packet["as_of"]) == "after_cutoff"
    assert availability("2026-09-21", packet["as_of"]) == "same_day_unknown"


def test_ratio_metadata_and_reviewed_unit_conversion_do_not_destroy_evidence():
    packet, fact = source_case()
    packet["sources"][0]["excerpt"] = fact["source_excerpt"] = "225 mil toneladas"
    fact.update(value=225000, kind="forecast", unit="tonnes", currency="not_applicable", observed_at=None, published_at=None, vintage=None)
    review = check("old")
    review["checks"].update(observed_at="not_applicable", published_at="unresolved", vintage="not_applicable")
    result = apply_fact_checks([fact], [review], packet)[0]
    assert fact_observation_is_supported(result)
    assert result["value_derivation"]["operation"] == "source_reviewed_conversion"
    review["checks"]["value"] = "not_applicable"
    assert not fact_observation_is_supported(apply_fact_checks([fact], [review], packet)[0])


def test_corrected_column_is_new_identity_with_original_retained_and_projected():
    packet, fact = source_case()
    original = deepcopy(fact)
    review = check("old")
    review["checks"]["value"] = "unsupported"
    review["correction"] = {"changes": {"value": 90.9}, "checks": check("x")["checks"], "reason": "August column is 90.9, 82.6 is 2023"}
    corrected = apply_fact_checks([fact], [review], packet)
    assert fact == original
    assert len(corrected) == 2
    assert corrected[0]["superseded_by"] == corrected[1]["id"]
    assert not fact_observation_is_supported(corrected[0])
    assert fact_observation_is_supported(corrected[1])
    projected = expand_observations(observation_brief({"facts": corrected, "source_packet": packet, "research_questions": []}, {"fact_ids": ["old"]}))
    assert {row["id"] for row in projected["facts"]} == {"old", corrected[1]["id"]}
    assert "Exact source" in projected["facts"][0]["source_review"]["reason"]


def test_explicit_contrary_comparison_survives_without_pulling_unrelated_archive():
    packet, fact = source_case()
    facts = [{**fact, "id": identifier, "comparison_groups": [group], "metric": metric}
             for identifier, group, metric in [("deficit", "balance", "Forecast shortfall"),
                ("surplus", "balance", "Refined surplus"), ("other", "healthcare", "Earnings")]]
    evidence = {"facts": facts, "source_packet": packet}
    case = {"asset_class": "copper", "fact_ids": ["deficit"], "contrary_evidence": [{"fact_ids": ["surplus"]}]}
    assert {row["id"] for row in evidence_for_decisions(evidence, case)["facts"]} == {"deficit", "surplus"}
    old_version = detail_basis(case, evidence)
    evidence["facts"][1]["value"] = 225000
    assert old_version != detail_basis(case, evidence)


def test_coverage_retains_established_parts_of_an_incomplete_dimension():
    packet, fact = source_case()
    good = {**fact, "id": "good"}
    bad = {**fact, "id": "bad", "verification_issues": ["Supporting excerpt not found in retrieved source"]}
    result = coverage({"question": "Costs?", "required_dimensions": ["costs"]}, {"facts": [good, bad], "source_packet": packet},
        [{"dimension": "costs", "status": "answered", "answer": "Some costs are available", "fact_ids": ["good", "bad"]}])
    assert result["status"] == "partial"
    assert result["answers"][0]["qualified_fact_ids"] == ["bad"]


def test_corrections_reach_exclusions_and_pricing_but_not_capital():
    original = {"excluded_opportunities": [{"reason": "Measured term premium"}], "asset_class_targets": [
        {"target_pct": 20, "market_pricing": {"observed_expectation": "Certain"}}],
        "smaller_change_alternative": {"rationale": "Executed"}}
    patches = [{"path": path, "original": old, "replacement": new, "reason": "Source correction", "fact_ids": []}
        for path, old, new in [(["excluded_opportunities", 0, "reason"], "Measured term premium", "Policy-yield spread"),
            (["asset_class_targets", 0, "market_pricing", "observed_expectation"], "Certain", "Uncertain"),
            (["smaller_change_alternative", "rationale"], "Executed", "Proposed"),
            (["asset_class_targets", 0, "target_pct"], 20, 30)]]
    fixed = apply_claim_patches(original, {"patches": patches})
    assert len(fixed["claim_corrections"]) == 3
    assert fixed["asset_class_targets"][0]["target_pct"] == 20
    assert fixed["unapplied_claim_corrections"][0]["rejection_reason"] == "numeric_or_structural_change"
    replayed = apply_claim_patches(fixed, {"patches": patches[:1]})
    assert replayed["unapplied_claim_corrections"][-1]["status"] == "superseded"


def test_new_bullion_and_point_weights_are_not_miner_capital():
    snapshot = {"portfolio": {"cash_pct": 0}, "asset_classes": [{"asset_class": "miners", "portfolio_pct": 100}]}
    proposal = {"asset_class_targets": [{"asset_class": "bullion", "position_identity": "new", "target_pct": 4,
        "baseline_links": [{"view": "holdings", "asset_class": "miners", "relationship": "partial_overlap", "capital_component": False}]}],
        "current_sleeve_actions": [{"asset_class": "miners", "action": "TRIM", "target_pct": 96}, {"asset_class": "cash", "action": "HOLD"}]}
    ledger = funding_ledger(snapshot, proposal)
    assert ledger["status"] == "balanced" and ledger["one_way_turnover_pct"] == 4
    assert ledger["rows"][0]["current_pct"] == 0
    assert ledger["trade_status"] == "proposed_not_executed"


def test_typed_nominal_real_pair_uses_issuer_currency_maturity_not_curve_name():
    _, fact = source_case()
    nominal = {**fact, "metric": "Treasury yield", "unit": "%", "measurement": {"issuer": "US Treasury", "maturity_months": 120, "price_basis": "nominal", "curve": "nominal par"}}
    real = {**nominal, "measurement": {**nominal["measurement"], "price_basis": "real", "curve": "TIPS real"}}
    assert not calculation_issues(nominal, real, "breakeven_spread")
    real["measurement"]["maturity_months"] = 60
    assert calculation_issues(nominal, real, "breakeven_spread")


def test_every_submitted_component_has_a_plan_without_invented_legs():
    plays = [{"id": "play", "components": [{"id": name, "name": name, "source_text": name} for name in ["fertiliser", "gold", "silver", "oil", "uranium", "gold over bonds"]]}]
    plan = complete_component_plan({"questions": [{"question": "Copper?", "component_ids": ["invented"]}]}, plays, {})
    assert {identifier for row in plan["questions"] for identifier in row.get("component_ids", [])} == {row["id"] for row in plays[0]["components"]}
    assert len(plan["component_coverage"]) == 6


def test_qualitative_scenarios_have_no_fabricated_returns():
    snapshot = {"portfolio": {"cash_pct": 100}, "asset_classes": []}
    proposal = {"asset_class_targets": [{"asset_class": "cash", "target_pct": 100}], "scenario_risks": [
        {"name": "Inflation", "assumptions": [{"claim": "Inflation remains high", "basis": "hypothetical"}],
         "exposures": [{"asset_class": "cash", "direction": "harm", "reason": "Purchasing power risk"}]}]}
    result = implementation_comparison(snapshot, proposal, {})
    scenario = result["destination"]["scenarios"][0]
    assert scenario["status"] == "qualitative" and scenario["proposed_return_pct"] is None
    assert scenario["rows"][0]["direction"] == "harm"


def test_monitor_binding_sign_persistence_and_stable_identity():
    condition = {"series_binding": {"metric": "spread", "benchmark": "LME copper", "unit": "USD/t", "quote_convention": "cash_minus_3m"},
        "operator": "gt", "threshold": 0, "max_age_days": 7, "consecutive_count": 2, "max_gap_days": 2}
    observations = [{**condition["series_binding"], "value": 36, "published_at": f"2026-09-{day}", "observed_at": f"2026-09-{day}", "source_url": "https://example.test"} for day in [19, 20]]
    result = evaluate_conditions([condition], observations, "2026-09-21")[0]
    assert result["status"] == "triggered" and result["id"]
    observations[0]["quote_convention"] = "contango_magnitude"
    result2 = evaluate_conditions([{**condition, "title": "Cosmetic change"}], observations, "2026-09-21")[0]
    assert result2["status"] == "unassessed" and result2["id"] == result["id"]


@pytest.mark.asyncio
async def test_short_pdf_excerpt_is_hydrated_once_and_failure_retains_excerpt(tmp_path, monkeypatch):
    fetch = AsyncMock(return_value={"sections": [{"page": 1, "text": "2023 2026-Aug\n82.6 90.9"}], "coverage": "selected_pages"})
    monkeypatch.setattr("backend.portfolio_documents.fetch_pdf_context", fetch)
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    def lane():
        return {"label": "macro", "parallel": {"results": [{"url": "https://example.test/report.pdf", "content": "Brent 82.6"}]}}
    a, b = lane(), lane()
    await asyncio.gather(hydrate_citations([a], runtime), hydrate_citations([b], runtime))
    assert fetch.await_count == 1
    assert "2026-Aug" in a["parallel"]["results"][0]["content"]
    fetch.side_effect = RuntimeError("Document unavailable")
    failed = lane()
    failed["parallel"]["results"][0]["url"] = "https://example.test/other.pdf"
    await hydrate_citations([failed], runtime)
    row = failed["parallel"]["results"][0]
    assert row["content"] == "Brent 82.6" and row["context_limitation"]


def test_pdf_layout_keeps_headers_above_their_values():
    import fitz
    document = fitz.open()
    page = document.new_page()
    for x, y, text in [(30, 30, "Period"), (150, 30, "2023"), (250, 30, "August 2026"),
                       (30, 50, "Brent"), (150, 50, "82.6"), (250, 50, "90.9")]:
        page.insert_text((x, y), text)
    context = pdf_context(document.tobytes(), "Brent")
    lines = context["sections"][0]["text"].splitlines()
    assert lines[0].index("2023") == lines[1].index("82.6")
    assert lines[0].index("August") == lines[1].index("90.9")


def test_frozen_run_retains_both_copper_surpluses_in_final_packet():
    path = Path("outputs/audits/portfolio-final-review-20260921/latest.json")
    if not path.exists():
        pytest.skip("Local frozen audit artifact is not distributed")
    run = json.loads(path.read_text())
    restored, _ = restore_phase_research(run["evidence_brief"], run, "challenge")
    packet = evidence_for_decisions(restored, run["macro_positioning"])
    ids = {fact["id"] for fact in packet["facts"]}
    aliases = restored.get("fact_aliases", {})
    for identifier in ["fact_f19a2b907dfe4f43f438", "fact_7f17d81f2903315bfdc6"]:
        assert aliases.get(identifier, identifier) in ids
    assert len(ids) < len(restored["facts"])


def test_frozen_world_bank_headers_distinguish_annual_and_monthly_prices():
    path = Path("outputs/audits/portfolio-final-review-20260921/world-bank-september-2026.pdf")
    if not path.exists():
        pytest.skip("Local publisher fixture is not distributed")
    lines = pdf_context(path.read_bytes(), "Brent WTI")["sections"][0]["text"].splitlines()
    periods = next(line for line in lines if "Jan-Dec" in line and "August" in line)
    years = next(line for line in lines if "2023" in line and "2025" in line)
    brent = next(line for line in lines if "Crude oil, Brent" in line)
    wti = next(line for line in lines if "Crude oil, WTI" in line)
    assert abs(years.index("2023") - brent.index("82.6")) < 5
    assert abs(periods.index("August") - brent.index("90.9")) < 5
    assert abs(periods.index("August") - wti.index("82.7")) < 5


@pytest.mark.asyncio
async def test_all_affordable_first_searches_start_without_wave_barrier(tmp_path, monkeypatch):
    from scripts import portfolio_positioning_memo as memo
    monkeypatch.setenv("PORTFOLIO_RESEARCH_BUDGET_USD", "1.20")
    monkeypatch.setenv("PORTFOLIO_FOLLOWUP_TASK_PRICE_USD", "0.60")
    started = set()
    both_started = asyncio.Event()
    async def gather(self, runtime, *, question, context, **options):
        started.add(question)
        if len(started) == 2:
            both_started.set()
        await asyncio.wait_for(both_started.wait(), 2)
        return {"results": [{"url": "https://example.test", "content": "100"}]}
    async def structure(lane, **kwargs):
        lane["evidence_brief"] = {"facts": [], "source_packet": {"sources": []}, "question_answers": []}
        return lane
    monkeypatch.setattr(memo.ParallelSourceProvider, "gather", gather)
    monkeypatch.setattr(memo, "_structure_evidence_lane", structure)
    questions = [{"question": name + " outlook?", "topic": name, "asset_classes": [name],
        "required_dimensions": ["outlook"], "material_reason": "Changes investment case", "reuse_assessment": "No evidence yet"}
        for name in ["Oil", "Uranium"]]
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    token = CURRENT_RUNTIME.set(runtime)
    try:
        _, runs, _ = await memo._run_question_research({}, "deep", {"phase": "independent", "questions": questions})
    finally:
        CURRENT_RUNTIME.reset(token)
    assert len(started) == 2 and len(runs) == 2
    assert not any(lane.get("error") for lane in runs)


@pytest.mark.asyncio
async def test_provider_preference_preserves_model_fallback_and_no_output_cap(tmp_path, monkeypatch):
    monkeypatch.setenv("PORTFOLIO_PROVIDER_SORT", "throughput")
    received = []
    async def client(model, messages, **settings):
        received.append((model, settings))
        await settings["on_progress"]({"activity": "provider_working", "reasoning_delta": "analysis"})
        await settings["on_progress"]({"activity": "receiving_text", "content_delta": '{"answer":"ok"}'})
        return {"content": '{"answer":"ok"}', "finish_reason": "stop", "usage": {"completion_tokens": 20}, "provider": "test"}
    client.supports_progress = client.supports_provider_preferences = True
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    result = await runtime.query(client, "chosen/model", [{"role": "user", "content": json.dumps({"task": "Test", "required_schema": {"answer": "string"}})}],
        parser=json.loads, validator=lambda value, prompt: [], max_tokens=32000)
    assert result["stage_status"] == "complete"
    model, settings = received[0]
    assert model == "chosen/model" and settings["provider_preferences"] == {"sort": "throughput", "allow_fallbacks": True}
    assert "max_tokens" not in settings
    assert runtime.receipts[-1]["timing"]["time_to_first_token_seconds"] is not None
    monkeypatch.setenv("PORTFOLIO_PROVIDER_SORT", "latency")
    await runtime.query(client, "chosen/model", [{"role": "user", "content": json.dumps({"task": "Test", "required_schema": {"answer": "string"}})}],
        parser=json.loads, validator=lambda value, prompt: [])
    assert len(received) == 1, "Changing serving policy must not repurchase completed analysis"


def test_research_horizon_and_scenario_role_contracts():
    from backend.portfolio_independent import allocation_prompt, review_prompt
    from scripts.portfolio_positioning_memo import _build_evidence_lane_specs
    neutral = {"research_cutoff": "2026-09-21", "investment_constraints": {"risk_tolerance": "high", "time_horizon": "5+ years"}}
    snapshot = {"portfolio": {"cash_pct": 100}, "asset_classes": []}
    blind = allocation_prompt("blind_macro_prior", {"facts": []}, neutral)
    assert blind["independent_context"]["investment_constraints"]["time_horizon"] == "5+ years"
    assert "scenario_risks" not in blind["required_schema"]
    defensive = review_prompt("defensive_regime_reviewer", {"facts": []}, neutral, {}, {}, snapshot, [])
    assert "scenario_risks" in defensive["required_schema"]
    assert "dominant 12-24 month portfolio regime" not in json.dumps(_build_evidence_lane_specs("test", "deep"))


@pytest.mark.asyncio
@pytest.mark.parametrize("exhausted", [False, True])
async def test_existing_source_answers_question_without_new_paid_discovery(tmp_path, monkeypatch, exhausted):
    from scripts import portfolio_positioning_memo as memo
    paid = AsyncMock(side_effect=AssertionError("No new paid search expected"))
    monkeypatch.setattr(memo.ParallelSourceProvider, "gather", paid)
    packet, fact = source_case()
    async def structure(lane, **kwargs):
        lane["evidence_brief"] = {"facts": [fact], "source_packet": packet, "question_answers": [
            {"dimension": "price", "status": "answered", "answer": "Source price retained", "fact_ids": [fact["id"]]}]}
        return lane
    monkeypatch.setattr(memo, "_structure_evidence_lane", structure)
    question = {"question": "What was Brent's monthly price?", "required_dimensions": ["price"], "asset_classes": ["energy"],
        "inspect_source_ids": ["s"], "material_reason": "Distinguish monthly and annual price", "reuse_assessment": "Inspect original table"}
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    if exhausted:
        from backend.portfolio_retrieval import ResearchBudget
        runtime.research_reservations["already_spent"] = {"estimate_usd": ResearchBudget(runtime).limit, "status": "reserved"}
    token = CURRENT_RUNTIME.set(runtime)
    try:
        _, runs, report = await memo._run_question_research({"facts": [], "source_packet": packet}, "deep", {"phase": "independent", "questions": [question]})
    finally:
        CURRENT_RUNTIME.reset(token)
    assert not paid.await_count and report["answered"] == 1
    assert runs[0]["question"]["reused_document"]


@pytest.mark.asyncio
async def test_initial_source_success_survives_processing_failure(tmp_path, monkeypatch):
    from scripts import portfolio_positioning_memo as memo
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    source = {"provider": "parallel", "results": [{"url": "https://example.test/report", "content": "Purchased source evidence"}]}
    monkeypatch.setattr(memo, "_run_research_lanes", AsyncMock(return_value=(source, {})))
    async def fail(lane, **kwargs):
        assert runtime.partial["evidence_runs"][0]["parallel"]["results"]
        assert runtime.checkpoint.exists()
        raise RuntimeError("Extraction unavailable")
    monkeypatch.setattr(memo, "_structure_evidence_lane", fail)
    token = CURRENT_RUNTIME.set(runtime)
    try:
        result = await memo._run_single_evidence_lane(query="Market outlook", mode="deep", asset_class_vocabulary=[],
            lane_label="macro", lane_focus="Market evidence", include_coverage_checklist=False)
    finally:
        CURRENT_RUNTIME.reset(token)
    assert result["parallel"]["results"] == source["results"]
    assert result["evidence_brief"]["stage_error"] == "Extraction unavailable"
