import asyncio
from copy import deepcopy

import pytest

from backend.portfolio_runtime import PortfolioRuntime, load_checkpoint
from backend.portfolio_work import check_and_develop_cases


@pytest.mark.asyncio
async def test_ready_case_starts_before_unrelated_source_tail(tmp_path):
    runtime = PortfolioRuntime(tmp_path / "cases.checkpoint.json", record_store=True)
    started = asyncio.Event()
    order = []
    async def verify(publish):
        await publish({"facts": [{"id": "a"}]}, {"a"})
        await asyncio.wait_for(started.wait(), 2)
        order.append("b checked")
        await publish({"facts": [{"id": "a"}, {"id": "b"}]}, {"b"})
        return {"facts": [{"id": "a"}, {"id": "b"}]}
    async def develop(case, evidence):
        assert case["fact_ids"] <= {row["id"] for row in evidence["facts"]}
        order.append(case["id"])
        if case["id"] == "a":
            started.set()
        return {"case": case["id"]}
    evidence, results = await check_and_develop_cases({}, [
        {"id": "a", "fact_ids": {"a"}}, {"id": "b", "fact_ids": {"b"}}], verify, develop, runtime)
    assert order == ["a", "b checked", "b"]
    assert results == [{"case": "a"}, {"case": "b"}]
    saved = load_checkpoint(runtime.checkpoint)
    assert len(saved["partial_artifact"]["developed_cases"]) == 2
    assert saved["partial_artifact"]["work_plan"]["nodes"]["investment_cases"]["status"] == "complete"


@pytest.mark.asyncio
async def test_failed_source_task_cancels_dependency_waiters(tmp_path):
    runtime = PortfolioRuntime(tmp_path / "cases.checkpoint.json", record_store=True)
    async def verify(publish):
        raise OSError("checkpoint storage unavailable")
    async def forbidden(*args):
        pytest.fail("Case without its dependencies was dispatched")
    with pytest.raises(OSError):
        await asyncio.wait_for(check_and_develop_cases({}, [{"id": "a", "fact_ids": {"a"}}],
            verify, forbidden, runtime), 2)


def test_common_scenarios_apply_identical_assumptions_to_four_views():
    from backend.portfolio_judgment import common_scenario_comparison
    snapshot = {"portfolio": {"cash_pct": 40}, "asset_classes": [{"asset_class": "gold", "portfolio_pct": 60}]}
    scenario = {"name": "Fiscal confidence shock", "horizon": "5 years", "mechanism": "Term premium rises",
        "assumptions": [{"claim": "Real yields rise", "basis": "hypothetical", "fact_ids": []}],
        "exposures": [{"asset_class": "gold", "direction": "mixed", "reason": "Currency versus real-rate effects"}]}
    ideal = {"asset_class_targets": [{"asset_class": "gold", "target_pct": 20}, {"asset_class": "cash", "target_pct": 80}]}
    final = {"asset_class_targets": [{"asset_class": "gold", "target_pct": 30}, {"asset_class": "cash", "target_pct": 70}],
        "scenario_risks": [scenario], "smaller_change_alternative": deepcopy(ideal)}
    original = deepcopy(final)
    result = common_scenario_comparison(snapshot, ideal, final, {})
    assert set(result["views"]) == {"current", "independent_ideal", "smaller_change", "final"}
    assert result["definitions"][0]["assumptions"][0]["claim"] == "Real yields rise"
    assert result["definitions"][0]["assumptions"][0]["reference_status"] == "hypothetical"
    for view in result["views"].values():
        assert view["scenarios"][0]["scenario_id"] == result["definitions"][0]["id"]
        assert view["scenarios"][0]["proposed_return_pct"] is None
    assert final == original


def test_explicit_case_alias_groups_but_substitute_does_not():
    from backend.portfolio_exposures import economic_case_aliases
    ideal = {"asset_class_targets": [{"asset_class": "bullion"}]}
    current = {"asset_class_targets": [
        {"asset_class": "gold_etf", "baseline_links": [{"view": "ideal", "asset_class": "bullion", "relationship": "equivalent"}]},
        {"asset_class": "miners", "baseline_links": [{"view": "ideal", "asset_class": "bullion", "relationship": "substitute"}]}]}
    aliases = economic_case_aliases(ideal, current, {})
    assert aliases["GOLDETF"] == aliases["BULLION"]
    assert aliases["MINERS"] != aliases["BULLION"]


def test_scenario_aliases_do_not_treat_substitutes_or_conflicting_directions_as_equivalent():
    from backend.portfolio_judgment import common_scenario_comparison
    snapshot = {"portfolio": {"cash_pct": 100}, "asset_classes": []}
    ideal = {"asset_class_targets": [{"asset_class": "bullion", "target_pct": 70},
                                   {"asset_class": "bond_ladder", "target_pct": 30}]}
    final = {"asset_class_targets": [
        {"asset_class": "gold_etf", "target_pct": 100, "baseline_links": [
            {"view": "ideal", "asset_class": "bullion", "relationship": "equivalent"},
            {"view": "ideal", "asset_class": "bond_ladder", "relationship": "substitute"}]}],
        "scenario_risks": [{"name": "Shock", "exposures": [{"asset_class": "gold_etf", "direction": "benefit"}]}]}
    before = deepcopy((ideal, final))
    result = common_scenario_comparison(snapshot, ideal, final, {})
    scenario = result["views"]["independent_ideal"]["scenarios"][0]
    assert scenario["directional_weight_pct"]["benefit"] == 70
    assert scenario["directional_weight_pct"]["unknown"] == 30
    assert (ideal, final) == before
    final["asset_class_targets"].append({"asset_class": "other_etf", "target_pct": 0,
        "baseline_links": [{"view": "ideal", "asset_class": "bullion", "relationship": "equivalent"}]})
    final["scenario_risks"][0]["exposures"].append({"asset_class": "other_etf", "direction": "hurt"})
    result = common_scenario_comparison(snapshot, ideal, final, {})
    assert result["views"]["independent_ideal"]["scenarios"][0]["directional_weight_pct"]["unknown"] == 100


def test_decisive_economics_rank_ahead_of_same_priority_quote_refresh():
    from backend.portfolio_research import prioritize_searches
    quote = {"id": "quote", "asset_classes": ["gold"], "critical_premise": True,
        "decision_impact": "high", "decision_dependency": "market_quote", "decision_consequence": "Refresh price"}
    margins = {**quote, "id": "margin", "asset_classes": ["producers"], "decision_dependency": "earnings",
        "decision_consequence": "Determine whether input costs absorb the revenue benefit"}
    assert [row["id"] for row in prioritize_searches([quote, margins], {})] == ["margin", "quote"]


@pytest.mark.asyncio
async def test_research_and_provider_state_use_events_after_initial_boundary(tmp_path):
    runtime = PortfolioRuntime(tmp_path / "research.checkpoint.json", record_store=True)
    await runtime.asave()
    before = runtime.checkpoint_metrics["writes"]
    async def fake():
        return {"summary": "Preserved research", "results": [{"url": "https://example.test/source"}]}
    await runtime.save_provider_task("task", {"status": "running", "run_id": "accepted-id"})
    await runtime.research("parallel", {"question": "A focused question"}, fake)
    assert runtime.checkpoint_metrics["writes"] == before
    saved = load_checkpoint(runtime.checkpoint)
    assert saved["provider_tasks"]["task"]["run_id"] == "accepted-id"
    assert saved["partial_artifact"]["retained_research"]


def test_html_context_keeps_table_hierarchy_caveats_and_dates_separate():
    from backend.portfolio_documents import html_context
    html = '''<html><head><meta property="article:published_time" content="2026-09-01"/></head><body>
    <nav>Brent wrong quote</nav><h1>Commodity prices</h1><h2>Oil</h2>
    <table><caption>Brent, USD per barrel</caption><tr><th rowspan="2">Commodity</th>
    <th colspan="2">Annual</th><th>Monthly</th></tr><tr><th>2023</th><th>2024</th><th>August 2026</th></tr>
    <tr><th scope="row">Brent</th><td>82.6</td><td>80.7</td><td>90.9</td></tr></table>
    <p>Monthly series are provisional; annual values are full-year averages.</p></body></html>'''
    result = html_context(html, "Brent August 2026 82.6")
    table = next(row for row in result["sections"] if row["method"] == "html-table-cells")
    assert table["heading_path"] == ["Commodity prices", "Oil"]
    assert table["rows"][0][1]["colspan"] == "2"
    assert table["rows"][1][2]["text"] == "August 2026"
    assert table["rows"][2][3]["text"] == "90.9"
    assert any("provisional" in row["text"] for row in result["sections"])
    assert result["publisher_metadata"]["article:published_time"] == "2026-09-01"
    assert "observed_at" not in result and "published_at" not in result
    assert "wrong quote" not in str(result)


@pytest.mark.asyncio
async def test_targeted_html_context_persists_incrementally_and_reuses_on_resume(tmp_path, monkeypatch):
    from unittest.mock import AsyncMock
    from backend.portfolio_sources import hydrate_citations
    fetch = AsyncMock(return_value={"sections": [{"section": 3, "text": "Verified surrounding table"}], "coverage": "selected_html_sections"})
    monkeypatch.setattr("backend.portfolio_documents.fetch_document_context", fetch)
    lanes = [{"label": "source", "parallel": {"results": [{"url": "https://example.test/table",
        "content": "Original excerpt", "context_required": True, "context_query": "Table columns"}]}}]
    runtime = PortfolioRuntime(tmp_path / "documents.checkpoint.json", record_store=True)
    await runtime.asave()
    before = runtime.checkpoint_metrics["writes"]
    first = await hydrate_citations(deepcopy(lanes), runtime)
    assert runtime.checkpoint_metrics["writes"] == before
    assert first[0]["parallel"]["results"][0]["original_excerpt"] == "Original excerpt"
    restored = PortfolioRuntime(runtime.checkpoint, resume=runtime.checkpoint, record_store=True)
    again = await hydrate_citations(deepcopy(lanes), restored)
    assert first == again and fetch.await_count == 1


def test_embedded_review_contract_survives_merge_and_rules_change():
    from backend.portfolio_evidence import apply_fact_checks, merge_briefs, reusable_fact_checks
    from tests.unit.test_portfolio_evidence_uplift import source_case, check
    packet, fact = source_case()
    reviewed = apply_fact_checks([fact], [check("old", check_contract="contract-a", check_model="model-a")], packet)
    merged = merge_briefs([{"facts": reviewed, "source_packet": packet}])
    same, pending = reusable_fact_checks(merged["facts"], merged["source_packet"], contract="contract-a")
    assert same and not pending and same[0]["check_model"] == "model-a"
    same, pending = reusable_fact_checks(merged["facts"], merged["source_packet"], contract="contract-b")
    assert not same and pending


def test_progress_plan_does_not_duplicate_the_fact_archive():
    from backend.portfolio_work import workflow_plan, plan_summary
    plan = workflow_plan()
    plan["nodes"]["source_checks"].update(status="admitted", cases=[{"fact_ids": ["a"]}], batch_fact_ids=[["a"]])
    summary = plan_summary(plan)
    assert "cases" not in summary["nodes"]["source_checks"]
    assert "batch_fact_ids" not in summary["nodes"]["source_checks"]
    assert summary["remaining_seconds"] is None and summary["unscoped_stages"] == len(plan["nodes"]) - 1
    for node in plan["nodes"].values():
        node["status"] = "complete"
    summary = plan_summary(plan)
    assert summary["remaining_seconds"] == 0 and summary["estimate_status"] == "finished"
