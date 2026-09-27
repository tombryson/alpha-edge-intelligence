import json
from copy import deepcopy
from unittest.mock import AsyncMock

import pytest

import portfolio_positioning_memo as memo
from backend.portfolio_evidence import normalize_facts, numeric_source_derivation
from backend.portfolio_independent import (
    establish_play_components, freeze_play_components, review_prompt, review_prompt_batches, run_financial_review,
)
from backend.portfolio_research import coverage, merge_question, normalize_questions, refresh_signed_evidence, remaining_search, planning_prompt
from backend.portfolio_runtime import CURRENT_RUNTIME, PortfolioRuntime
from backend.portfolio_tasks import investment_evidence, evidence_for_decisions
from backend.portfolio_retrieval import ParallelSourceProvider
from backend.routers.runs import _build_portfolio_read_models


def brief():
    return {"facts": [{"id": "flow", "metric": "Inventory change", "value": -95, "unit": "million barrels",
        "kind": "observed_macro", "benchmark": "Global oil stocks", "currency": "not_applicable",
        "observed_at": "2026-08-31", "published_at": "2026-09-11", "vintage": "September",
        "source_ids": ["iea"], "source_excerpt": "Inventories plunged by 95 million barrels."}],
        "source_packet": {"as_of": "2026-09-19", "sources": [{"id": "iea", "url": "https://example.org/oil",
            "published_at": "2026-09-11", "excerpt": "Inventories plunged by 95 million barrels."}]}}


def question(**values):
    return {"question": "What do oil stocks and exports establish?", "topic": "oil", "economic_question": "physical_balance",
        "geography": "global", "period": "September 2026", "horizon": "12 months",
        "required_dimensions": ["inventories", "exports"], "asset_classes": ["energy"],
        "status": "unanswered", "material_reason": "Tests supply normalization", "reuse_assessment": "Prices do not establish supply",
        "decision_impact": "high", "critical_premise": True, **values}


def answer(dimension="inventories", **values):
    return {"dimension": dimension, "status": "answered", "answer": "Measured inventory draw", "fact_ids": ["flow"], **values}


@pytest.mark.parametrize("magnitude,excerpt", [
    (-95, "Inventories plunged by a further 95 million barrels."),
    (-507, "Cumulative draws since February total 507 million barrels."),
    (-507, "Inventories plunged by 95 mb, taking cumulative draws since February to 507 mb."),
    (-65, "Oil on water volumes declined by 65 million barrels."),
    (-52, "Non-OECD stocks drew 52 million barrels."),
])
def test_signed_draws_are_supported_without_changing_the_observation(magnitude, excerpt):
    data = brief()
    data["source_packet"]["sources"][0]["excerpt"] = excerpt
    data["facts"][0].update(value=magnitude, source_excerpt=excerpt)
    result = normalize_facts(data["facts"], data["source_packet"])[0]
    assert not result["verification_issues"]
    assert result["value"] == magnitude
    assert result["value_derivation"]["operation"] == "signed_change"
    assert result["claim_status"] == "unresolved", "A numeric match is not a completed financial source review"


@pytest.mark.parametrize("metric,excerpt", [
    ("Inventory change", "Inventories rose by 95 million barrels."),
    ("Inventory change", "Inventories fell to 95 million barrels."),
    ("Inventory level", "Inventories declined by 95 million barrels."),
    ("Inventory change", "Exports fell by 10. Inventories reached 95 million barrels."),
    ("Inventory change", "A 95 million barrel inventory level."),
])
def test_direction_cannot_be_invented_or_borrowed_from_another_clause(metric, excerpt):
    assert numeric_source_derivation({"metric": metric, "value": -95}, excerpt) is None


def test_old_signed_verification_warning_is_repaired_without_mutating_the_artifact():
    data = brief()
    issue = "Claimed numeric value is not in the supporting excerpt; a derivation must be reviewed"
    data["facts"][0]["verification_issues"] = [issue, "Missing published_at"]
    original = deepcopy(data)
    fixed = refresh_signed_evidence(data)
    assert fixed["facts"][0]["verification_issues"] == ["Missing published_at"]
    assert coverage(question(required_dimensions=["inventories"]), fixed, [answer()])["status"] == "answered"
    assert original == data


def test_partial_answer_survives_deferred_plan_and_failed_followup():
    data = brief()
    old = normalize_questions([question(answers=[answer()])], data)[0]
    later = normalize_questions([question(status="deferred", answers=[answer(status="unresolved", answer="", fact_ids=[])])], data)[0]
    result = merge_question(old, later, data)
    assert result["status"] == "partial"
    assert result["answers"][0]["answer"] == "Measured inventory draw"
    assert result["missing_dimensions"] == ["exports"]
    assert remaining_search(result)["required_dimensions"] == ["exports"]
    result["searched_dimensions"] = ["exports"]
    assert remaining_search(result) is None
    result["required_dimensions"].append("refinery demand")
    result.update(coverage(result, data, result["answers"]))
    assert remaining_search(result)["required_dimensions"] == ["refinery demand"]


def test_sourced_conflict_remains_visible_and_stale_answers_are_revalidated():
    data = brief()
    row = question(required_dimensions=["inventories"])
    assert coverage(row, data, [answer(), answer(status="conflicting", answer="Different definitions disagree")])["status"] == "conflicting"
    data["facts"][0]["review_dimensions"] = {"observation": "unsupported"}
    assert coverage(row, data, [answer()])["status"] == "unanswered"


def test_explicit_answer_continuity_preserves_scope_without_discovery_fanout():
    data = brief()
    data["research_questions"] = [question(id="old", period="2026", answers=[]),
        question(id="new", reuse_question_id="old", period="2027", status="partial", answers=[answer()])]
    data["facts"].append({**deepcopy(data["facts"][0]), "id": "unrelated", "benchmark": "Other geography",
        "research_question_ids": ["old"], "comparison_groups": ["oil"]})
    original = deepcopy(data)
    packet = evidence_for_decisions(data, {"research_question_ids": ["old"]})
    assert {f["id"] for f in packet["facts"]} == {"flow"}
    old = next(q for q in packet["research_questions"] if q["question_id"] == "old")
    assert old["status"] == "partial" and old["scope_status"] == "unanswered"
    new = next(q for q in packet["research_questions"] if q["question_id"] == "new")
    assert old["period"] == "2026" and new["period"] == "2027"
    assert old["related_answer_ids"] == ["new"] and new["answers"][0]["fact_ids"] == ["flow"]
    planner = planning_prompt("challenge", data, {"research_cutoff": "2026-09-23"})
    assert planner["research_registry"][0]["related_answer_ids"] == ["new"]
    assert data == original


@pytest.mark.asyncio
async def test_later_phase_searches_only_new_dimensions_and_saves_distinct_phase_records(tmp_path, monkeypatch):
    data = brief()
    row = normalize_questions([question(answers=[answer()], searched_dimensions=["inventories"])], data)[0]
    data["research_questions"] = [row]
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    gather = AsyncMock(return_value={"provider": "parallel", "results": [{"url": "https://example.org/oil", "content": "Saved research"}]})
    monkeypatch.setattr(ParallelSourceProvider, "gather", gather)
    async def structure(lane, **kwargs):
        assert lane["question"]["required_dimensions"] == ["exports"]
        lane["evidence_brief"] = {**brief(), "question_answers": [answer("exports", status="partial", answer="Only some export flows established")]}
        return lane
    monkeypatch.setattr(memo, "_structure_evidence_lane", structure)
    token = CURRENT_RUNTIME.set(runtime)
    try:
        result, _, report = await memo._run_question_research(data, "deep", {"phase": "current", "questions": [question()]})
        checked = result["research_questions"][0]
        assert checked["answers"][0]["status"] == "answered"
        assert checked["answers"][1]["status"] == "partial"
        assert gather.call_args.kwargs["context"]["required_dimensions"] == ["exports"]
        assert next(iter(runtime.partial["targeted_research_results"])).startswith("current:")
        _, followups, _ = await memo._run_question_research(result, "deep", {"phase": "plays", "questions": [question()]})
        assert not followups and gather.await_count == 1
        assert report["questions"][0]["status"] == "partial"
    finally:
        CURRENT_RUNTIME.reset(token)


@pytest.mark.asyncio
async def test_deferred_retrieval_does_not_replace_partial_coverage(tmp_path, monkeypatch):
    monkeypatch.setenv("PORTFOLIO_RESEARCH_BUDGET_USD", "0.001")
    data = brief()
    data["research_questions"] = normalize_questions([question(answers=[answer()])], data)
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    gather = AsyncMock(side_effect=AssertionError("No budget for research"))
    monkeypatch.setattr(ParallelSourceProvider, "gather", gather)
    token = CURRENT_RUNTIME.set(runtime)
    try:
        result, _, _ = await memo._run_question_research(data, "deep", {"phase": "current", "questions": [question()]})
        assert result["research_questions"][0]["status"] == "partial"
        assert result["research_questions"][0]["retrieval_status"] == "deferred"
    finally:
        CURRENT_RUNTIME.reset(token)


@pytest.mark.asyncio
async def test_old_checkpoint_restores_extracted_answers_without_paid_research(tmp_path, monkeypatch):
    data = brief()
    data["facts"][0]["verification_issues"] = ["Claimed numeric value is not in the supporting excerpt; a derivation must be reviewed"]
    row = normalize_questions([question(required_dimensions=["inventories"], answers=[answer()])], data)[0]
    row.update(retrieval_status="succeeded", processing_status="complete")
    data["research_questions"] = [row]
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    runtime.partial["targeted_research_results"] = {"old_lane": {"question": deepcopy(row),
        "phase": "plays", "evidence_brief": {**brief(), "question_answers": [answer()]}}}
    gather = AsyncMock(side_effect=AssertionError("Do not repeat saved research"))
    monkeypatch.setattr(ParallelSourceProvider, "gather", gather)
    token = CURRENT_RUNTIME.set(runtime)
    try:
        result, searches, report = await memo._run_question_research(data, "deep", {"phase": "plays", "questions": [row]})
        assert not searches and not gather.await_count
        assert report["answered"] == 1 and result["research_questions"][0]["status"] == "answered"
    finally:
        CURRENT_RUNTIME.reset(token)


@pytest.mark.asyncio
async def test_distinct_question_gets_research_before_an_expansion(tmp_path, monkeypatch):
    monkeypatch.setenv("PORTFOLIO_RESEARCH_BUDGET_USD", "0.01")
    provider = ParallelSourceProvider(api_key="test", processor="ultra2x")
    provider.gather = AsyncMock(return_value={"results": [{"url": "https://example.org/oil", "content": "Source"}],
        "expansion_query": "Research the same topic again"})
    monkeypatch.setattr(memo, "ParallelSourceProvider", lambda: provider)
    async def structure(lane, **kwargs):
        lane["evidence_brief"] = brief()
        return lane
    monkeypatch.setattr(memo, "_structure_evidence_lane", structure)
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    token = CURRENT_RUNTIME.set(runtime)
    try:
        _, searches, _ = await memo._run_question_research(brief(), "deep", {"phase": "independent", "questions": [question(),
            question(topic="fertiliser", economic_question="margins", question="What are fertiliser margins?")]})
        assert len(searches) == 2
        assert provider.gather.await_count == 2
        assert "fertiliser" in provider.gather.call_args_list[1].kwargs["question"]
    finally:
        CURRENT_RUNTIME.reset(token)


def plays():
    return [{"id": "scarcity", "title": "Scarcity", "thesis": "Fertiliser and uranium producers"},
            {"id": "hedge", "title": "Preferred hedge", "thesis": "Physical gold over government bonds"}]


@pytest.mark.asyncio
async def test_component_repair_is_scoped_and_preserves_a_frozen_inventory():
    existing = freeze_play_components(plays(), [{"play_id": "hedge", "coverage_status": "complete",
        "coverage_reason": "The complete idea is one relative hedge preference.", "unresolved_source_text": [],
        "components": [{"economic_key": "gold_over_bonds",
        "name": "Gold over bonds", "source_text": plays()[1]["thesis"], "direction": "relative_preference"}]}])
    model = AsyncMock(return_value={"play_components": [{"play_id": "scarcity", "coverage_status": "complete",
        "coverage_reason": "Fertiliser and uranium are each represented.", "unresolved_source_text": [], "components": [
        {"economic_key": name.lower(), "name": name, "source_text": name, "direction": "long"}
        for name in ("Fertiliser", "uranium")]}]})
    result = await establish_play_components(existing, [], model, "configured-model", "2026-09-19")
    assert result[1] == existing[1]
    assert len(result[0]["components"]) == 2
    prompt = model.call_args.args[2]
    assert len(prompt["investment_plays"]) == 1 and "evidence_brief" not in prompt
    assert "short" not in {component["direction"] for play in result for component in play["components"]}
    await establish_play_components(result, [], model, "configured-model", "2026-09-19")
    assert model.await_count == 1


def test_review_sees_new_uncited_research_and_keeps_all_observations():
    data = brief()
    data["facts"][0]["interpretations"] = ["Old narrative repeated" * 100]
    data["market_view"] = {"summary": "Earlier normalization thesis"}
    data["research_questions"] = normalize_questions([question(answers=[answer()])], data)
    proposal = {"asset_class_targets": [{"asset_class": "energy", "target_pct": 6, "rationale": "Prices fell", "fact_ids": []}]}
    original = deepcopy(data)
    packet = investment_evidence(data)
    assert len(packet["facts"]) == len(data["facts"])
    assert "interpretations" not in packet["facts"][0]
    assert packet["facts"][0]["value"] == -95
    assert "initial_market_context" in packet and "market_view" not in packet
    prompt = review_prompt("defensive_regime_reviewer", data, {"research_cutoff": "2026-09-19"}, proposal, proposal, {}, [])
    assert prompt["research_attention"][0]["question_id"] == data["research_questions"][0]["id"]
    assert prompt["evidence_brief"]["facts"][0]["id"] == "flow"
    assert data == original


@pytest.mark.asyncio
async def test_completed_review_part_survives_a_later_interruption(tmp_path, monkeypatch):
    import backend.portfolio_independent as independent
    prompts = [{"task": "first"}, {"task": "second"}]
    monkeypatch.setattr(independent, "review_prompt_batches", lambda *args: prompts)
    call = AsyncMock(side_effect=[{"stage_status": "complete", "summary": "Saved challenge", "findings": []}, RuntimeError("credit required")])
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    with pytest.raises(RuntimeError, match="credit required"):
        await run_financial_review("defensive_regime_reviewer", "configured", {}, {}, {}, {}, {}, [], call, runtime)
    assert list(runtime.partial["analytical_review_batches"]["defensive_regime_reviewer"].values())[0]["summary"] == "Saved challenge"
    saved = json.loads(runtime.checkpoint.read_text())
    assert saved["partial_artifact"]["analytical_review_batches"]


@pytest.mark.asyncio
async def test_failed_optional_part_keeps_successful_review_and_reports_the_gap(tmp_path, monkeypatch):
    import backend.portfolio_independent as independent
    monkeypatch.setattr(independent, "review_prompt_batches", lambda *args: [{"task": "one"}, {"task": "two"}])
    call = AsyncMock(side_effect=[{"stage_status": "complete", "summary": "Valid review", "findings": [{"argument": "Measured disruption"}]},
        {"stage_status": "failed", "error": "Provider unavailable"}])
    result = await run_financial_review("reviewer", "model", {}, {}, {}, {}, {}, [], call, PortfolioRuntime(tmp_path / "state.json"))
    assert result["stage_status"] == "complete" and result["findings"]
    assert result["warnings"][0]["detail"] == "Provider unavailable"


@pytest.mark.asyncio
async def test_review_sections_do_not_replay_prior_narratives(tmp_path, monkeypatch):
    import backend.portfolio_independent as independent
    monkeypatch.setattr(independent, "review_prompt_batches", lambda *args: [
        {"task": "physical evidence", "review_scope": {"question_ids": ["physical"]}},
        {"task": "play assessment", "review_scope": {"question_ids": ["producer margins"]}}])
    call = AsyncMock(side_effect=[{"stage_status": "complete", "summary": "The supply premise is contradicted",
        "findings": [{"argument": "Inventories drew down", "fact_ids": ["flow"]}]},
        {"stage_status": "complete", "summary": "Assess producer valuations against physical scarcity"}])
    result = await run_financial_review("reviewer", "model", brief(), {}, {}, {}, {}, [], call, PortfolioRuntime(tmp_path / "state.json"))
    prompt = call.call_args_list[1].args[2]
    assert "earlier_review_sections" not in prompt
    assert "Inventories drew down" not in json.dumps(prompt)
    assert result["findings"][0]["fact_ids"] == ["flow"]


def test_incomplete_reader_shows_saved_proposals_without_rewriting_original(tmp_path):
    proposal = {"executive_summary": "Physical supply remains disrupted.",
        "asset_class_targets": [{"asset_class": "energy", "target_pct": 6, "rationale": "Retain a smaller exposure."}]}
    data = {"analysis_kind": "portfolio_positioning", "workflow_version": 4, "pipeline_status": "awaiting_credit",
        "portfolio_snapshot": {"portfolio": {"cash_pct": .425997}}, "independent_ideal": proposal,
        "current_portfolio_assessment": {**proposal, "executive_summary": "Reduce concentration, not conviction."},
        "structured_data": {"analysis_kind": "portfolio_positioning", "executive_summary": "Portfolio analysis is in progress."},
        "analyst_memo_markdown": "# Original partial", "evidence_brief": brief()}
    path = tmp_path / "partial.json"
    path.write_text(json.dumps(data))
    original = path.read_bytes()
    result = _build_portfolio_read_models(path, data)["memo"]
    assert result["structured_data"]["is_partial"]
    assert result["structured_data"]["portfolio_diagnosis"]["current_cash_pct"] == .425997
    body = result["memo_markdown"]
    assert "additional API credit" in body and "is in progress" not in body
    assert body.index("Independent Ideal Portfolio") < body.index("Supporting Research")
    assert body.index("Assessment Of Your Portfolio") < body.index("Supporting Research")
    assert "Draft weight" in body and "6%" in body
    assert "Reconciling The Two Views" not in body and "Implementation And Alternatives" not in body
    assert "Recommended Portfolio" not in body
    assert path.read_bytes() == original


def test_review_assigns_cases_not_a_new_obligation_per_archived_question():
    data = brief()
    data["facts"] = [{**data["facts"][0], "id": f"f{index}", "source_excerpt": (f"Unique source {index}. " * 180)} for index in range(12)]
    data["research_questions"] = normalize_questions([question(economic_question=f"q{index}",
        answers=[answer(fact_ids=[f"f{index}"])]) for index in range(12)], data)
    proposal = {"asset_class_targets": [{"asset_class": "cash", "target_pct": 100}]}
    parts = review_prompt_batches("reviewer", data, {"research_cutoff": "2026-09-19"}, proposal, proposal, {}, plays(), packet_chars=30000)
    assert len(parts) == 1
    ids = {row["question_id"] for part in parts for row in part["evidence_brief"].get("research_questions", [])}
    assert not ids, "Unrelated research must not become standalone review work"
    assert [play["id"] for part in parts for play in part["investment_plays"]] == [play["id"] for play in plays()]
    for part in parts:
        packet = part["evidence_brief"]
        assert not packet["facts"]
        assert not any(case.startswith("question.") for case in part["review_scope"]["case_ids"])
    proposal["strategic_view"] = "Review portfolio-wide risks"
    parts = review_prompt_batches("reviewer", data, {"research_cutoff": "2026-09-19"}, proposal, proposal, {}, [])
    assert {row[0] for part in parts for row in part["evidence_brief"]["other_observations"]["rows"]} == {row["id"] for row in data["facts"]}
    assert {row["question_id"] for part in parts for row in part["research_attention"]} == {row["id"] for row in data["research_questions"]}


def test_reader_shapes_use_recorded_weights_and_do_not_normalize_missing_capital(tmp_path):
    def targets(gold, cash):
        return {"asset_class_targets": [{"asset_class": "gold", "target_pct": gold}, {"asset_class": "cash", "target_pct": cash}]}
    final = {**targets(35, 65), "smaller_change_alternative": targets(38, 62)}
    payload = {"workflow_version": 4, "analysis_kind": "portfolio_positioning", "macro_positioning": final,
        "portfolio_snapshot": {"portfolio": {"cash_pct": 60}, "asset_classes": [{"asset_class": "gold", "portfolio_pct": 40}]},
        "independent_ideal": targets(25, 75), "structured_data": targets(35, 65)}
    path = tmp_path / "memo.json"
    path.write_text(json.dumps(payload))
    before = deepcopy(payload)
    shapes = _build_portfolio_read_models(path, payload)["memo"]["structured_data"]["portfolio_shapes"]
    assert [row["id"] for row in shapes] == ["current", "ideal", "recommended", "smaller"]
    assert all(row["status"] == "balanced" for row in shapes)
    assert [view["rows"][0]["target_pct"] for view in shapes] == [40, 25, 35, 38]
    assert payload == before
    payload["independent_ideal"]["asset_class_targets"][0]["target_pct"] = 30
    shapes = _build_portfolio_read_models(path, payload)["memo"]["structured_data"]["portfolio_shapes"]
    assert shapes[1]["status"] == "unresolved" and shapes[1]["rows"][0]["target_pct"] == 30
