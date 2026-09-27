import argparse
from copy import deepcopy
import json
from unittest.mock import AsyncMock

import pytest

import portfolio_positioning_memo as memo
from backend import portfolio_judgment as judgment
from backend.portfolio_requests import reader_decision
from backend.portfolio_runtime import PortfolioRuntime


@pytest.mark.asyncio
@pytest.mark.parametrize("change", [None, "context", "model", "stale_commentary", "missing_writer", "review_unavailable"])
async def test_final_review_recovery_never_replays_completed_research(tmp_path, monkeypatch, change):
    final = {"asset_class_targets": [{"asset_class": "gold", "target_pct": 100}], "executive_summary": "Settled view"}
    context = {"mandate": {"risk_tolerance": "high", "time_horizon": "5+ years"}, "investment_plays": [{"thesis": "Scarcity"}]}
    commentary = {"comparison_summary": "The revised financial case"}
    saved = {"portfolio_context": context, "portfolio_snapshot": {}, "macro_positioning": final,
        "independent_ideal": {"asset_class_targets": [{"asset_class": "gold", "target_pct": 100}]},
        "current_portfolio_assessment": {"executive_summary": "Independent current view"},
        "analytical_reviews": [], "evidence_brief": {"facts": []}, "workflow_version": 4,
        "pipeline_status": "awaiting_credit", "funding": {"status": "insufficient"}, "pipeline_error": "Old credit estimate"}
    writer = {"stage": "memo_commentary_after_reconsideration:Write", "model": "writer/model", "status": "complete",
        "retained_output": commentary, "prompt": {"final_recommendation": reader_decision(final)}}
    review = {"stage": "decision_consistency:Check", "model": "review/model", "status": "complete",
        "prompt": {"contract": "independent-portfolio-v1", "rules": ["Retain supported decisions"]}}
    if change == "stale_commentary":
        writer["prompt"]["final_recommendation"] = {"executive_summary": "Old allocation"}
    runtime = PortfolioRuntime()
    runtime.previous_receipts = [review] if change == "missing_writer" else [review, writer]
    checkpoint = tmp_path / "source.checkpoint.json"
    checkpoint.write_text(json.dumps({"partial_artifact": saved}))
    before = checkpoint.read_bytes()
    request_context = deepcopy(context)
    if change == "context":
        request_context["mandate"]["risk_tolerance"] = "low"
    context_file = tmp_path / "context.json"
    context_file.write_text(json.dumps(request_context))
    args = argparse.Namespace(resume_checkpoint=str(checkpoint), portfolio_context_file=str(context_file),
        dump_json=str(tmp_path / "recovered.json"), run_label="Recovery")
    monkeypatch.setattr(memo, "allocator_assignments_from_environment", lambda: [
        {"role": "defensive_regime_reviewer", "model": "changed/model" if change == "model" else "review/model"}])
    monkeypatch.setattr(memo, "_commentary_model_for_mode", lambda mode: "writer/model")
    monkeypatch.setattr(judgment, "consistency_inputs", lambda *args: {})
    monkeypatch.setattr(judgment, "decision_checks", lambda *args: {"computed_claims": []})
    monkeypatch.setattr(judgment, "apply_claim_patches", lambda document, *args: document)
    monkeypatch.setattr(judgment, "decision_revision_scope", lambda *args: {"asset_classes": []})
    monkeypatch.setattr(memo, "_finish_independent_artifact", lambda artifact, final, commentary, review, runtime:
        {**artifact, "macro_positioning": final, "allocator_commentary": commentary, "consistency": review})
    runtime.query = AsyncMock(return_value={"stage_status": "failed", "error": "Review not funded", "content": ""}
        if change == "review_unavailable" else {"stage_status": "complete", "content": json.dumps({"summary": "Checked", "patches": []})})
    result = await memo._resume_final_review(args, runtime)
    assert checkpoint.read_bytes() == before
    if change in {"context", "model", "stale_commentary", "missing_writer"}:
        assert result is None
        runtime.query.assert_not_awaited()
        return
    runtime.query.assert_awaited_once()
    prompt = json.loads(runtime.query.call_args.args[2][0]["content"])
    assert prompt["task"] == "Verify the settled document after targeted reconsideration; preserve all decisions"
    assert result["portfolio_context"] == context
    assert result["macro_positioning"]["asset_class_targets"] == final["asset_class_targets"]
    assert result["allocator_commentary"]["comparison_summary"] == commentary["comparison_summary"]
    assert "funding" not in result and "pipeline_error" not in result
    assert all(row["reused"] for row in runtime.receipts)
    assert result["provenance"]["recovery_scope"] == "settled_document"
    if change == "review_unavailable":
        assert result["consistency"]["stage_status"] == "failed"
        assert result["consistency"]["remaining_concerns"]
