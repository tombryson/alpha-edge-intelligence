from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import portfolio_positioning_memo as memo
from backend import portfolio_independent as independent
from backend.portfolio_repair import load_review_continuation
from backend.portfolio_runtime import CURRENT_RUNTIME, PortfolioRuntime, digest


def saved_run(tmp_path):
    context = {"portfolio": {"cash_pct": 100}, "asset_classes": [], "investment_plays": []}
    proposal = {"stage_status": "complete", "asset_class_targets": [{"asset_class": "cash", "target_pct": 100}]}
    saved = {"portfolio_context": context, "portfolio_snapshot": deepcopy(context),
        "independent_ideal": proposal, "current_portfolio_assessment": deepcopy(proposal),
        "evidence_brief": {"facts": [{"id": "f", "metric": "Yield", "value": 4}], "research_questions": []},
        "baseline_branches": {key: {"status": "sealed", "input_hash": key} for key in ("independent", "current")},
        "investment_plays": [], "research_phases": [{"phase": "current", "status": "deferred"}],
        "analytical_review_batches": {"defensive_regime_reviewer": {"part": {"stage_status": "complete"}}}}
    path = tmp_path / "original.checkpoint.json"
    path.write_text(json.dumps({"workflow_version": 4, "research_cutoff": "2026-09-21T13:48:56Z", "partial_artifact": saved}))
    return context, saved, path


def test_review_boundary_preserves_original_case_and_all_research(tmp_path):
    context, saved, path = saved_run(tmp_path)
    result = load_review_continuation({**context, "frozen_research_query": "saved query"}, path, tmp_path / "new.json")
    assert result["resume_boundary"] == "financial_reviews"
    assert result["source_saved_state_hash"] == digest(saved)
    assert "source_artifact_hash" not in result
    for key in ("independent_ideal", "current_portfolio_assessment", "evidence_brief", "research_phases", "baseline_branches"):
        assert result[key] == saved[key]
    result["evidence_brief"]["facts"].clear()
    assert json.loads(path.read_text())["partial_artifact"]["evidence_brief"]["facts"]


@pytest.mark.parametrize("field", ["portfolio", "investment_plays", "investment_constraints"])
def test_changed_brief_cannot_be_relabelled_as_recovery(tmp_path, field):
    context, _, path = saved_run(tmp_path)
    with pytest.raises(ValueError, match="original portfolio"):
        load_review_continuation({**context, field: {"changed": True}}, path)


def test_partial_or_later_boundary_is_not_mistaken_for_review_continuation(tmp_path):
    context, _, path = saved_run(tmp_path)
    data = json.loads(path.read_text())
    data["partial_artifact"]["provisional_recommendation"] = {"asset_class_targets": [{"asset_class": "cash"}]}
    path.write_text(json.dumps(data))
    assert load_review_continuation(context, path) is None
    del data["partial_artifact"]["provisional_recommendation"]
    data["partial_artifact"]["baseline_branches"]["current"]["status"] = "retained_partial"
    path.write_text(json.dumps(data))
    assert load_review_continuation(context, path) is None


def test_original_is_not_overwritten_and_reassessment_is_separate(tmp_path):
    context, _, path = saved_run(tmp_path)
    with pytest.raises(ValueError, match="overwrite"):
        load_review_continuation(context, path, tmp_path / "original.json")
    assert load_review_continuation({**context, "repair_preserve_baselines": True}, path) is None


@pytest.mark.asyncio
async def test_pipeline_enters_review_without_replaying_research_or_allocators(tmp_path, monkeypatch):
    context, saved, path = saved_run(tmp_path)
    context_path = tmp_path / "context.json"
    context_path.write_text(json.dumps(context))
    runtime = PortfolioRuntime(tmp_path / "recovered.checkpoint.json", path)
    runtime.query = AsyncMock(side_effect=AssertionError("Completed research must not be queried"))
    async def stop_at_review(role, model, evidence, neutral, ideal, current, snapshot, plays, call, rt):
        assert evidence == saved["evidence_brief"]
        assert ideal == saved["independent_ideal"]
        assert current == saved["current_portfolio_assessment"]
        assert rt.partial["baseline_branches"] == saved["baseline_branches"]
        raise RuntimeError("Reached preserved review boundary")
    monkeypatch.setattr(independent, "run_financial_review", stop_at_review)
    token = CURRENT_RUNTIME.set(runtime)
    try:
        with pytest.raises(RuntimeError, match="preserved review boundary"):
            await memo._run_independent_pipeline(SimpleNamespace(portfolio_context_file=str(context_path),
                resume_checkpoint=str(path), dump_json=str(tmp_path / "recovered.json"), mode="deep"))
    finally:
        CURRENT_RUNTIME.reset(token)
    runtime.query.assert_not_awaited()


@pytest.mark.asyncio
async def test_model_change_retains_completed_sections_and_only_dispatches_unfinished(tmp_path, monkeypatch):
    prompts = [{"task": "one"}, {"task": "two"}]
    monkeypatch.setattr(independent, "review_prompt_batches", lambda *args: prompts)
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    runtime.partial.update(review_continuation={"source_run_id": "original"},
        analytical_review_batches={"defensive_regime_reviewer": {digest(prompts[0]): {
            "stage_status": "complete", "model": "anthropic/claude-opus-5", "summary": "Saved Opus finding",
            "request_hash": digest(prompts[0]), "findings": []}}})
    call = AsyncMock(return_value={"stage_status": "complete", "model": "~deepseek/deepseek-flash-latest", "findings": []})
    result = await independent.run_financial_review("defensive_regime_reviewer", "~deepseek/deepseek-flash-latest",
        {}, {}, {}, {}, {}, [], call, runtime)
    assert call.await_count == 1 and call.call_args.args[2] == prompts[1]
    assert result["models"] == ["anthropic/claude-opus-5", "~deepseek/deepseek-flash-latest"]
    assert result["review_parts"][0]["reused"]
    assert result["review_completion"] == "complete"
    assert runtime.progress.snapshot()["phases"][0]["reused"] == 1


@pytest.mark.asyncio
async def test_completed_source_lookup_is_not_repeated_after_it_updates_findings(tmp_path, monkeypatch):
    prompt = {"task": "Review", "evidence_brief": {"facts": []}}
    monkeypatch.setattr(independent, "review_prompt_batches", lambda *args: [prompt])
    evidence = {"facts": [{"id": "f", "metric": "Price", "value": 95, "source_excerpt": "Brent: 95"}]}
    call = AsyncMock(side_effect=[{"stage_status": "complete", "findings": [],
        "evidence_requests": [{"fact_ids": ["f"], "reason": "Establish the price benchmark"}]},
        {"stage_status": "complete", "finding_updates": [{"finding_id": None,
            "asset_class": "energy", "argument": "The quote is for Brent", "fact_ids": ["f"]}]}])
    runtime = PortfolioRuntime(tmp_path / "first.checkpoint.json")
    before = await independent.run_financial_review("reviewer", "model", evidence, {}, {}, {}, {}, [], call, runtime)
    runtime.partial["review_continuation"] = {"source_run_id": "first"}
    call.reset_mock(side_effect=True)
    call.side_effect = AssertionError("Completed source lookup must not repeat")
    after = await independent.run_financial_review("reviewer", "model", evidence, {}, {}, {}, {}, [], call, runtime)
    call.assert_not_awaited()
    from backend.portfolio_judgment import prepare_reviews
    assert after["findings"] == prepare_reviews([before])[0]["findings"]
    assert after["evidence_lookup"]["request_hash"] == before["evidence_lookup"]["request_hash"]


@pytest.mark.asyncio
async def test_changed_section_input_is_not_reused(tmp_path, monkeypatch):
    old = {"task": "review", "case": "old evidence"}
    new = {"task": "review", "case": "new evidence"}
    monkeypatch.setattr(independent, "review_prompt_batches", lambda *args: [new])
    runtime = PortfolioRuntime(tmp_path / "checkpoint.json")
    runtime.partial.update(review_continuation={"source_run_id": "old"},
        analytical_review_batches={"reviewer": {digest(old): {"stage_status": "complete", "findings": []}}})
    call = AsyncMock(return_value={"stage_status": "complete", "findings": []})
    await independent.run_financial_review("reviewer", "new/model", {}, {}, {}, {}, {}, [], call, runtime)
    call.assert_awaited_once()
