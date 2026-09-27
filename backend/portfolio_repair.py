"""Opt-in repair of downstream decisions, preserving the original two views."""

import json
from copy import deepcopy
from pathlib import Path

from .portfolio_independent import independent_context
from .portfolio_runtime import digest, load_checkpoint


def load_review_continuation(context, checkpoint, destination=None):
    """Resume the saved review boundary without reopening sealed research branches."""
    if not checkpoint or context.get("repair_preserve_baselines"):
        return None
    path = Path(checkpoint)
    payload = load_checkpoint(path)
    saved = payload.get("partial_artifact") or {}
    if payload.get("workflow_version", 0) < 4 or saved.get("provisional_recommendation"):
        return None
    if not saved.get("analytical_review_batches"):
        return None
    ignored = {"frozen_research_query", "frozen_company_evidence"}
    original_context = saved.get("portfolio_context") or {}
    if {k: v for k, v in context.items() if k not in ignored} != {k: v for k, v in original_context.items() if k not in ignored}:
        raise ValueError("Review recovery requires the original portfolio, mandate and plays.")
    branches = saved.get("baseline_branches") or {}
    if any((branches.get(key) or {}).get("status") != "sealed" for key in ("independent", "current")):
        return None
    if not all((saved.get(key) or {}).get("asset_class_targets") for key in ("independent_ideal", "current_portfolio_assessment")):
        return None
    if not (saved.get("evidence_brief") or {}).get("facts"):
        return None
    source = path.with_name(path.name.replace(".checkpoint.json", ".json"))
    if destination and source.resolve() == Path(destination).resolve():
        raise ValueError("Recovery must not overwrite the original portfolio artifact.")
    return {"source_run_id": source.name, "source_saved_state_hash": digest(saved),
        "source_checkpoint_hash": digest(payload), "resume_boundary": "financial_reviews",
        "baseline_hashes": {key: digest(saved[key]) for key in ("independent_ideal", "current_portfolio_assessment")},
        "research_cutoff": payload.get("research_cutoff"),
        **{key: deepcopy(saved.get(key)) for key in ("independent_ideal", "current_portfolio_assessment",
            "evidence_brief", "evidence_runs", "source_citations", "investment_plays", "research_phases",
            "baseline_branches", "analytical_review_batches", "portfolio_snapshot")}}


def load_frozen_baselines(context, checkpoint, destination=None):
    if not context.get("repair_preserve_baselines"):
        return None
    if not checkpoint:
        raise ValueError("Baseline-preserving repair requires the original checkpoint.")
    path = Path(checkpoint)
    source = path.with_name(path.name.replace(".checkpoint.json", ".json"))
    if source == path or not source.is_file():
        raise ValueError("Original portfolio artifact is unavailable; no baseline has been invented.")
    if destination and source.resolve() == Path(destination).resolve():
        raise ValueError("A repaired analysis must not overwrite its original memo.")
    original = json.loads(source.read_text())
    prior_context = original.get("portfolio_context") or {}
    for field in ("portfolio", "asset_classes", "positions", "risk_exposures", "scenarios"):
        if context.get(field) != prior_context.get(field):
            raise ValueError(f"The saved {field} changed; start a new analysis rather than relabel old views.")
    if independent_context(context, "same") != independent_context(prior_context, "same"):
        raise ValueError("The investment brief changed; frozen baselines cannot assess a different mandate.")
    for field in ("independent_ideal", "current_portfolio_assessment"):
        if not (original.get(field) or {}).get("asset_class_targets"):
            raise ValueError(f"The source has no completed {field} to preserve.")
    if not (original.get("evidence_brief") or {}).get("facts"):
        raise ValueError("The source has no saved evidence to repair from.")
    return {"source_run_id": source.name, "source_artifact_hash": digest(original),
            "baseline_hashes": {field: digest(original[field]) for field in ("independent_ideal", "current_portfolio_assessment")},
            "research_cutoff": (original.get("provenance") or {}).get("research_cutoff"),
            **{field: deepcopy(original.get(field)) for field in ("independent_ideal", "current_portfolio_assessment",
                "evidence_brief", "evidence_runs", "source_citations")}}
