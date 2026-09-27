"""Research correctness must not add review rounds or duplicate paid work."""

from copy import deepcopy
from unittest.mock import AsyncMock

import pytest

from scripts.audit_portfolio_research_architecture import alias_probe, conflicting_answer_probe, evidence, question
from scripts import portfolio_positioning_memo as memo
from backend.portfolio_research import coverage, normalize_questions, research_readthrough, saved_source_lane
from backend.portfolio_runtime import CURRENT_RUNTIME, PortfolioRuntime, load_checkpoint


def test_conflicting_answer_order_cannot_change_the_selected_evidence():
    result = conflicting_answer_probe()
    assert result["forward"] == result["reversed"]
    assert result["forward"]["status"] == "conflicting"
    assert {ref for answer in result["forward"]["answers"] for ref in answer["fact_ids"]} == {"increase", "decrease"}


def test_alias_scope_keeps_contrary_evidence_without_an_extra_lookup():
    result = alias_probe()
    assert result["facts_from_alias_only"] == result["facts_with_explicit_question_link"] == ["contrary"]
    from backend.portfolio_exposures import decision_relationships
    assert decision_relationships({"asset_class": "Gold", "aliases": 3, "question_id": {}})["assets"] == {"GOLD"}
    assert decision_relationships({"aliases": "Gold"})["assets"] == set()


def test_review_packets_keep_aliases_at_the_actual_model_boundary():
    from backend.portfolio_independent import review_prompt_batches
    brief = evidence()
    brief["facts"] = [{"id": "contrary", "source_ids": ["primary"], "metric": "Real yields", "value": "rising"}]
    brief["research_questions"] = [{"id": "gold_q", "question": "Real yield opportunity cost?", "asset_classes": ["BULLION"],
        "answers": [{"answer": "Rising", "dimension": "cost", "fact_ids": ["contrary"]}]}]
    parts = review_prompt_batches("defensive_regime_reviewer", brief, {"research_cutoff": "2026-09-23"}, {},
        {"asset_class_targets": [{"asset_class": "GOLD_ETF", "aliases": ["BULLION"], "target_pct": 10}]}, {}, [])
    assert parts[0]["current_assessment"]["asset_class_targets"][0]["aliases"] == ["BULLION"]
    assert "question.gold_q" not in parts[0]["review_scope"]["case_ids"]
    assert parts[0]["review_scope"]["question_ids"] == ["gold_q"]
    assert parts[0]["evidence_brief"]["facts"][0]["id"] == "contrary"


def test_saved_source_reuse_requires_the_actual_query_not_just_question_id():
    row = normalize_questions([question()])[0]
    lane = {"phase": "independent", "question": row, "query": row["question"],
        "parallel": {"results": [{"content": "Original report"}]}}
    saved = {"targeted_research_results": {"first": lane}}
    assert saved_source_lane(row, saved, "current") == lane
    assert saved_source_lane({**row, "question": "A different primary-source lookup?"}, saved, "current") is None
    assert saved_source_lane(row, saved, "independent") == lane
    lane["phase"] = "plays"
    assert saved_source_lane(row, saved, "independent") is None


@pytest.mark.asyncio
async def test_expansion_buys_new_sources_and_resume_does_not_repeat(tmp_path, monkeypatch):
    calls = []
    async def gather(self, runtime, **kwargs):
        calls.append(kwargs["question"])
        return {"provider": "parallel", "results": [{"url": f"https://example.org/{len(calls)}", "content": f"Packet {len(calls)}"}],
            "expansion_query": "What does the primary export table establish?" if len(calls) == 1 else ""}
    async def structure(lane, **kwargs):
        lane["evidence_brief"] = evidence()
        return lane
    monkeypatch.setenv("PORTFOLIO_RESEARCH_BUDGET_USD", "3")
    monkeypatch.setenv("PORTFOLIO_FOLLOWUP_TASK_PRICE_USD", "0.6")
    monkeypatch.setattr(memo.ParallelSourceProvider, "gather", gather)
    monkeypatch.setattr(memo, "_structure_evidence_lane", structure)
    runtime = PortfolioRuntime(tmp_path / "research.json", record_store=True)
    token = CURRENT_RUNTIME.set(runtime)
    try:
        await runtime.asave()
        before = runtime.checkpoint_metrics["writes"]
        brief, lanes, _ = await memo._run_question_research(evidence(), "deep", {"phase": "independent", "questions": [question()]})
        assert len(calls) == len(lanes) == 2
        assert lanes[0]["parallel"]["results"] != lanes[1]["parallel"]["results"]
        assert runtime.checkpoint_metrics["writes"] - before <= 1
    finally:
        CURRENT_RUNTIME.reset(token)
    restored = PortfolioRuntime(runtime.checkpoint, resume=runtime.checkpoint, record_store=True)
    token = CURRENT_RUNTIME.set(restored)
    try:
        _, lanes, _ = await memo._run_question_research(brief, "deep", {"phase": "current", "questions": [question()]})
        assert not lanes and len(calls) == 2
        assert len(load_checkpoint(restored.checkpoint)["partial_artifact"]["targeted_research_results"]) == 2
    finally:
        CURRENT_RUNTIME.reset(token)


@pytest.mark.asyncio
async def test_new_primary_document_is_inspected_once_without_another_search(tmp_path, monkeypatch):
    brief = evidence()
    row = normalize_questions([question()], brief)[0]
    row["searched_dimensions"] = list(row["required_dimensions"])
    brief["research_questions"] = [row]
    inspections = []
    async def structure(lane, **kwargs):
        inspections.append(lane["query"])
        lane["evidence_brief"] = evidence()  # Still unresolved: no automatic paid fallback.
        return lane
    gather = AsyncMock(side_effect=AssertionError("No new paid search was admitted"))
    monkeypatch.setattr(memo.ParallelSourceProvider, "gather", gather)
    monkeypatch.setattr(memo, "_structure_evidence_lane", structure)
    requested = {**question(), "inspect_source_ids": ["primary"]}
    runtime = PortfolioRuntime(tmp_path / "inspection.json", record_store=True)
    token = CURRENT_RUNTIME.set(runtime)
    try:
        first, lanes, _ = await memo._run_question_research(brief, "deep", {"phase": "current", "questions": [requested]})
        assert len(lanes) == len(inspections) == 1 and lanes[0]["source_inspection"]
        assert first["research_questions"][0]["status"] == "unanswered"
        _, lanes, _ = await memo._run_question_research(first, "deep", {"phase": "challenge", "questions": [requested]})
        assert not lanes and len(inspections) == 1 and gather.await_count == 0
        first["source_packet"]["sources"][0]["excerpt"] = "New version of the dated primary table"
        _, lanes, _ = await memo._run_question_research(first, "deep", {"phase": "challenge", "questions": [requested]})
        assert len(lanes) == 1 and len(inspections) == 2 and gather.await_count == 0
    finally:
        CURRENT_RUNTIME.reset(token)


def test_coverage_is_idempotent_and_preserves_answer_qualifications():
    brief = evidence()
    brief["facts"] = [{"id": "f", "value": 2, "source_ids": ["primary"]}]
    row = question()
    answers = [{"dimension": "export volumes", "answer": "Two", "status": "answered", "fact_ids": ["f"]}]
    once = coverage(row, brief, answers)
    twice = coverage(row, brief, [*once["answers"], *deepcopy(once["answers"])])
    assert twice == once
    reading = research_readthrough({**brief, "research_questions": [{"id": "q", **row, **once}]})
    assert reading[0]["answers"][0]["support_status"] == "unverified"


def test_different_periods_and_explicit_corrections_are_not_false_conflicts():
    brief = evidence()
    fact = {"id": "a", "value": 2, "kind": "forecast", "metric": "Export change", "unit": "mb/d",
        "benchmark": "Gulf", "target_period": "2026-Q4", "source_ids": ["primary"]}
    brief["facts"] = [fact, {**fact, "id": "b", "value": -2, "target_period": "2027-Q1"}]
    answers = [{"dimension": "export volumes", "answer": ref, "status": "answered", "fact_ids": [ref]} for ref in ("a", "b")]
    assert coverage(question(), brief, answers)["status"] == "answered"
    brief["facts"][1]["target_period"] = "2026-Q4"
    assert coverage(question(), brief, answers)["status"] == "conflicting"
    brief["facts"][0]["superseded_by"] = "b"
    corrected = coverage(question(), brief, answers)
    assert corrected["status"] == "answered" and corrected["answers"][0]["fact_ids"] == ["b"]


@pytest.mark.asyncio
async def test_pending_expansion_resumes_exact_context_without_new_search(tmp_path, monkeypatch):
    calls = []
    async def gather(self, runtime, **kwargs):
        calls.append(deepcopy(kwargs))
        if len(calls) == 2:
            return {"error": "Saved task still pending", "resumable": True, "results": [], "request_id": "trun_saved"}
        return {"results": [{"url": "https://example.org/release", "content": "Saved release"}],
            "expansion_query": "What does the port register report?"}
    async def structure(lane, **kwargs):
        lane["evidence_brief"] = evidence()
        return lane
    monkeypatch.setenv("PORTFOLIO_RESEARCH_BUDGET_USD", "3")
    monkeypatch.setenv("PORTFOLIO_FOLLOWUP_TASK_PRICE_USD", "0.6")
    monkeypatch.setattr(memo.ParallelSourceProvider, "gather", gather)
    monkeypatch.setattr(memo, "_structure_evidence_lane", structure)
    runtime = PortfolioRuntime(tmp_path / "pending.json", record_store=True)
    token = CURRENT_RUNTIME.set(runtime)
    try:
        first, _, _ = await memo._run_question_research(evidence(), "deep", {"phase": "independent", "questions": [question()]})
        assert len(calls) == 2
    finally:
        CURRENT_RUNTIME.reset(token)
    restored = PortfolioRuntime(runtime.checkpoint, resume=runtime.checkpoint, record_store=True)
    token = CURRENT_RUNTIME.set(restored)
    try:
        _, lanes, _ = await memo._run_question_research(first, "deep", {"phase": "current", "questions": [question()]})
        assert len(calls) == 3 and len(lanes) == 1
        assert calls[1] == calls[2]  # Provider identity stays stable even with a changed evidence registry.
    finally:
        CURRENT_RUNTIME.reset(token)


@pytest.mark.asyncio
async def test_document_inspection_cannot_spend_the_last_discovery_slot_twice(tmp_path, monkeypatch):
    calls = []
    async def gather(self, runtime, **kwargs):
        calls.append(kwargs["question"])
        return {"results": []}
    async def structure(lane, **kwargs):
        lane["evidence_brief"] = evidence()
        return lane
    monkeypatch.setenv("PORTFOLIO_RESEARCH_BUDGET_USD", "0.005")
    monkeypatch.setenv("PORTFOLIO_FOLLOWUP_TASK_PRICE_USD", "0.6")
    monkeypatch.setattr(memo.ParallelSourceProvider, "gather", gather)
    monkeypatch.setattr(memo, "_structure_evidence_lane", structure)
    runtime = PortfolioRuntime(tmp_path / "budget.json", record_store=True)
    token = CURRENT_RUNTIME.set(runtime)
    try:
        second = {**question(), "question": "What is the unrelated sovereign yield?", "economic_question": "sovereign yields",
            "topic": "bonds", "asset_classes": ["bonds"], "required_dimensions": ["yield"]}
        _, lanes, _ = await memo._run_question_research(evidence(), "deep", {"phase": "independent", "questions": [
            {**question(), "inspect_source_ids": ["primary"]}, second]})
        assert len(lanes) == 2 and calls == [second["question"]]
    finally:
        CURRENT_RUNTIME.reset(token)
