import argparse
from copy import deepcopy
import json
from unittest.mock import AsyncMock

import pytest

from backend.portfolio_completion import load_completion, close_source_checks, retained_details, compact_completion_prompt, NOTE
from backend.portfolio_evidence import apply_fact_checks, normalize_facts, review_fields
from backend.portfolio_independent import independent_context, normalize_plays
from backend.portfolio_judgment import detail_basis
from backend.portfolio_runtime import CURRENT_LANE, CURRENT_RUNTIME, PortfolioRuntime, PortfolioDependencyError, digest
from scripts import portfolio_positioning_memo as memo
from tests.unit.test_portfolio_independent import snapshot, target, evidence, empty_shape, CUTOFF


def saved_run(tmp_path):
    context = {**snapshot(), "mandate": {"risk_tolerance": "high", "time_horizon": "5+ years"},
        "investment_plays": [{"title": "Scarcity", "thesis": "Precious metals and supply constraints"}]}
    proposal = {"asset_class_targets": [target("ENERGY", 40), target("CASH", 60)],
        "executive_summary": "Saved investment judgment", "stage_status": "complete", "play_assessments": []}
    brief = evidence()
    brief["facts"] = normalize_facts(brief["facts"], brief["source_packet"])
    original = {"portfolio_context": context, "portfolio_snapshot": memo._compact_snapshot(context),
        "investment_plays": normalize_plays(context["investment_plays"]),
        "independent_research_context": independent_context(context, CUTOFF), "query": "Original research query",
        "baseline_branches": {key: {"status": "sealed"} for key in ("independent", "current")},
        "independent_ideal": deepcopy(proposal), "current_portfolio_assessment": deepcopy(proposal),
        "provisional_recommendation": deepcopy(proposal), "evidence_brief": brief, "analytical_review_batches": {},
        "research_phases": [{"phase": "challenge", "status": "researched"}], "evidence_runs": [],
        "analytical_reviews": [{"council_lane": role, "stage_status": "complete", "findings": []}
            for role in ("exposure_equivalence_reviewer", "defensive_regime_reviewer")],
        "source_check_plan": {"fact_ids": ["f1"]}, "funding": {"status": "insufficient"},
        "pipeline_error": "Historical credit block"}
    checkpoint = tmp_path / "original.checkpoint.json"
    checkpoint.write_text(json.dumps({"workflow_version": 4, "partial_artifact": original, "research_cutoff": CUTOFF}))
    return context, original, checkpoint


@pytest.mark.parametrize("invalid", ["no_checkpoint", "overwrite", "mandate", "missing_baseline", "missing_review", "missing_proposal"])
def test_finish_recovery_requires_valid_unchanged_saved_inputs(tmp_path, invalid):
    context, original, checkpoint = saved_run(tmp_path)
    destination = tmp_path / "new.json"
    if invalid == "mandate":
        context["mandate"]["risk_tolerance"] = "low"
    elif invalid == "overwrite":
        destination = tmp_path / "original.json"
    elif invalid == "missing_baseline":
        original["baseline_branches"] = {}
    elif invalid == "missing_review":
        original["analytical_reviews"] = []
    elif invalid == "missing_proposal":
        original.pop("provisional_recommendation")
    if invalid.startswith("missing"):
        checkpoint.write_text(json.dumps({"workflow_version": 4, "partial_artifact": original}))
    runtime = PortfolioRuntime()
    with pytest.raises(ValueError):
        load_completion(context, None if invalid == "no_checkpoint" else checkpoint, destination, runtime)
    assert not getattr(runtime, "completion_recovery", None)


@pytest.mark.asyncio
async def test_closing_checks_preserves_adverse_verdicts_and_does_not_certify_unchecked_claims(tmp_path):
    context, original, checkpoint = saved_run(tmp_path)
    runtime = PortfolioRuntime()
    load_completion(context, checkpoint, tmp_path / "new.json", runtime)
    brief = original["evidence_brief"]
    fact = brief["facts"][0]
    checks = {field: "unresolved" for field in review_fields(fact)}
    checks["value"] = "unsupported"
    brief["facts"] = apply_fact_checks([fact], [{"fact_id": "f1", "checks": checks, "reason": "Source contradicts the value",
        "check_model": "original-model", "check_contract": "original-rules"}], brief["source_packet"])
    brief["facts"].append({**fact, "id": "unchecked"})
    before = deepcopy(brief["facts"])
    callback = AsyncMock()
    closed = await close_source_checks(brief, runtime, {"f1", "unchecked"}, callback)
    assert closed["facts"] == before
    assert closed["facts"][0]["claim_status"] == "unsupported"
    assert closed["source_check_completion"]["unverified_fact_ids"] == ["unchecked"]
    assert closed["source_check_completion"]["retained_check_fact_ids"] == ["f1"]
    callback.assert_awaited_once()
    assert NOTE in closed["research_limitations"]


def test_completed_cases_require_same_decision_and_evidence(tmp_path):
    _, saved, _ = saved_run(tmp_path)
    rows, brief = saved["provisional_recommendation"]["asset_class_targets"], saved["evidence_brief"]
    detail = {"asset_class": rows[0]["asset_class"], "detail_status": "current",
        "investment_case": {"downside": "A commodity price reversal reduces cash flow"},
        "detail_decision_hash": detail_basis(rows[0]), "detail_evidence_hash": detail_basis(rows[0], brief)}
    saved["investment_details"] = {"asset_class_targets": [detail]}
    assert retained_details(rows, saved, brief) == [detail]
    changed = deepcopy(brief)
    changed["facts"][0]["value"] = 5
    assert not retained_details(rows, saved, changed)
    assert not retained_details([{**rows[0], "target_pct": 45}], saved, brief)


def test_completed_case_reuses_citations_added_by_its_answer(tmp_path):
    _, saved, _ = saved_run(tmp_path)
    row = {**saved["provisional_recommendation"]["asset_class_targets"][0], "fact_ids": []}
    brief = saved["evidence_brief"]
    detail = {**row, "detail_status": "current", "investment_case": {
        "downside": "A commodity price reversal reduces cash flow",
        "causal_chain": [{"claim": "Energy prices affect cash flows", "fact_ids": ["f1"]}]}}
    detail["detail_decision_hash"] = detail_basis(row)
    detail["detail_evidence_hash"] = detail_basis(detail, brief)
    saved["investment_details"] = {"asset_class_targets": [detail]}
    assert detail_basis(row, brief) != detail["detail_evidence_hash"]
    assert retained_details([row], saved, brief) == [detail]
    changed = deepcopy(brief)
    changed["facts"][0]["value"] = 5
    assert not retained_details([row], saved, changed)


def test_completion_prompt_verdict_sharing_is_lossless_and_preserves_adverse_checks():
    verdict = {"status": "unresolved", "reason": "Source support has not been assessed",
        "dimensions": {field: "unresolved" for field in ("observation", "units_and_currency", "observation_date")}}
    adverse = {"status": "unsupported", "reason": "The source contradicts this value"}
    prompt = {"evidence_brief": {"observations": {"columns": ["id", "value", "source_review"],
        "rows": [["f1", 10, verdict], ["f2", 20, verdict], ["f3", 30, adverse]]}}, "rules": ["Retain uncertainty"]}
    original = deepcopy(prompt)
    compact = compact_completion_prompt(prompt)
    table = compact["evidence_brief"]["observations"]
    assert len(table["source_reviews"]) == 1
    assert table["rows"][0][2] == table["rows"][1][2] == {"source_review_ref": "review_1"}
    assert table["rows"][2][2] == adverse
    assert compact_completion_prompt(compact) == compact
    for row in table["rows"]:
        if "source_review_ref" in row[2]:
            row[2] = table["source_reviews"][row[2]["source_review_ref"]]
    table.pop("source_reviews")
    table.pop("source_review_encoding")
    assert compact == original == prompt


def test_chained_recovery_keeps_original_archive_and_completed_counts(tmp_path):
    context, saved, checkpoint = saved_run(tmp_path)
    saved["preserved_research_archive"] = {"source_run_id": "original_research.json"}
    saved["evidence_runs"] = [{"label": "macro", "source_archive": {"run_id": "original_research.json", "field": "evidence_runs"}}]
    checkpoint.write_text(json.dumps({"workflow_version": 4, "partial_artifact": saved}))
    runtime = PortfolioRuntime()
    runtime.previous_receipts = [{"status": "complete", "input_hash": str(i)} for i in range(3)]
    loaded = load_completion(context, checkpoint, tmp_path / "new.json", runtime)
    assert runtime.completion_recovery["preserved_completed_checkpoint_entries"] == 3
    assert loaded["preserved_research_archive"]["parent_archive"]["source_run_id"] == "original_research.json"
    assert loaded["evidence_runs"][0]["source_archive"]["run_id"] == "original_research.json"


def test_finish_recovery_references_raw_archive_without_copying_it(tmp_path):
    context, saved, checkpoint = saved_run(tmp_path)
    saved["document_inspections"] = {"raw": "Retained original source text"}
    saved["evidence_runs"] = [{"label": "macro", "model": "original-model", "supplementary": False,
        "evidence_brief": {"facts": [{"text": "Saved raw claim"}], "stage_status": "complete"}}]
    checkpoint.write_text(json.dumps({"workflow_version": 4, "partial_artifact": saved}))
    original = checkpoint.read_bytes()
    runtime = PortfolioRuntime()
    runtime.partial["document_inspections"] = saved["document_inspections"]
    runtime.cache["saved"] = {"receipt": {"status": "complete", "input_hash": "saved"}, "result": {"content": "Archived response"}}
    loaded = load_completion(context, checkpoint, tmp_path / "new.json", runtime)
    assert not runtime.cache
    assert runtime.completion_recovery["preserved_completed_checkpoint_entries"] == 1
    assert runtime.completion_recovery["preserved_cache_checkpoint"] == str(checkpoint)
    assert "document_inspections" not in runtime.partial
    assert "document_inspections" not in loaded
    assert "document_inspections" in loaded["preserved_research_archive"]["fields"]
    assert loaded["evidence_runs"][0]["model"] == "original-model"
    assert "facts" not in loaded["evidence_runs"][0]["evidence_brief"]
    assert loaded["evidence_brief"] == saved["evidence_brief"]
    assert checkpoint.read_bytes() == original


@pytest.mark.asyncio
@pytest.mark.parametrize("fail_stage", [None, "final_allocation", "memo_commentary"])
async def test_finish_pipeline_never_dispatches_research_reviews_or_source_checks(tmp_path, monkeypatch, fail_stage):
    context, saved, checkpoint = saved_run(tmp_path)
    original_bytes = checkpoint.read_bytes()
    context_file = tmp_path / "context.json"
    context_file.write_text(json.dumps(context))
    args = argparse.Namespace(resume_checkpoint=str(checkpoint), portfolio_context_file=str(context_file),
        dump_json=str(tmp_path / "finished.json"), run_label="Finish", mode="deep", query="", finish_from_saved_research=True)
    calls = []
    async def query(model, messages, **kwargs):
        assert CURRENT_LANE.get() in {"investment_cases", "final_allocation", "final_investment_cases", "memo_commentary"}
        prompt = json.loads(messages[0]["content"])
        task = prompt["task"]
        calls.append(task)
        if CURRENT_LANE.get() == fail_stage:
            return {"error": "openrouter_http_400", "error_status": 400, "content": ""}
        assert not any(text in task.lower() for text in ("review source support", "research questions", "independent ideal", "current portfolio independently"))
        result = empty_shape(prompt["required_schema"])
        if "target_updates" in result:
            result.update(reason="Retain the saved proposal", target_updates=[], updates={})
        elif "allocation_details" in result:
            result["allocation_details"] = [{"asset_class": row["asset_class"], "implementation": {}, "market_pricing": {},
                "investment_case": {"downside": "Commodity cash flows may decline"}, "alternatives": []}
                for row in prompt["assigned_allocations"]]
        elif "comparison_summary" in result:
            result.update(comparison_summary="Retain a measured exposure to the scarcity thesis, alongside liquidity.",
                portfolio_level_comments=["The chosen mix balances opportunity against uncertainty."], asset_class_comments=[])
        elif "patches" in result:
            result.update(summary="Preserved uncertainty and allocation arithmetic", patches=[], finding_checks=[], decision_revisions=[], remaining_concerns=[])
        return {"content": json.dumps(result), "finish_reason": "stop"}
    forbidden = AsyncMock(side_effect=AssertionError("Sealed work was reopened"))
    monkeypatch.setattr(memo, "query_model", query)
    monkeypatch.setattr(memo, "_run_evidence_ensemble", forbidden)
    monkeypatch.setattr(memo, "_run_targeted_research", forbidden)
    monkeypatch.setattr("backend.portfolio_independent.run_financial_review", forbidden)
    runtime = PortfolioRuntime(tmp_path / "finished.checkpoint.json", resume=checkpoint)
    token = CURRENT_RUNTIME.set(runtime)
    try:
        if fail_stage:
            with pytest.raises(PortfolioDependencyError, match="saved analysis is preserved, not complete"):
                await memo._run_pipeline(args)
            assert checkpoint.read_bytes() == original_bytes
            assert runtime.partial.get("pipeline_status") != "complete"
            assert digest(runtime.partial["provisional_recommendation"]) == digest(saved["provisional_recommendation"])
            forbidden.assert_not_awaited()
            return
        artifact = await memo._run_pipeline(args)
    finally:
        CURRENT_RUNTIME.reset(token)
    assert checkpoint.read_bytes() == original_bytes
    for field in ("independent_ideal", "current_portfolio_assessment", "analytical_reviews", "portfolio_snapshot"):
        assert digest(artifact[field]) == digest(saved[field])
    assert artifact["completion_recovery"]["new_source_checks_allowed"] is False
    assert artifact["completion_recovery"]["new_research_allowed"] is False
    assert artifact["provenance"]["recovery_scope"] == "finish_from_saved_research"
    assert NOTE in artifact["analyst_memo_markdown"]
    assert sum(row["target_pct"] for row in artifact["macro_positioning"]["asset_class_targets"]) == 100
    assert artifact["allocator_commentary"]["comparison_summary"]
    assert artifact["macro_positioning"]["consistency_review"]["stage_status"] == "not_run"
    assert artifact["completion_recovery"]["additional_model_review"] == "not_run"
    forbidden.assert_not_awaited()
    assert calls
