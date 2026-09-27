"""Explicit completion from saved research; never silently bypass new-run checks."""

from copy import deepcopy
from collections import Counter
import hashlib
import json
from pathlib import Path

from .portfolio_evidence import reusable_fact_checks
from .portfolio_judgment import detail_basis, substantive_details
from .portfolio_runtime import digest, load_checkpoint


NOTE = ("This assessment uses the saved research and completed source checks. "
        "Remaining source checks were closed at the user's request, not verified; "
        "unsupported or unverified claims remain qualified.")

ARCHIVE_FIELDS = {"targeted_research_results", "document_inspections", "research_lane_archive",
    "source_extractions", "document_sections", "observation_checks", "model_request_state",
    "research_phase_results", "structured_data", "analyst_memo_markdown", "chairman_memo_markdown"}


def checkpoint_hash(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_completion(context, checkpoint, destination, runtime):
    if not checkpoint:
        raise ValueError("Finish-only recovery requires a saved checkpoint.")
    path = Path(checkpoint)
    source = path.with_name(path.name.replace(".checkpoint.json", ".json"))
    if Path(destination).resolve() in {path.resolve(), source.resolve()}:
        raise ValueError("Finish-only recovery must preserve the original files.")
    payload = load_checkpoint(path)
    saved = payload.get("partial_artifact") or {}
    ignored = {"frozen_research_query", "frozen_company_evidence"}
    clean = lambda value: {k: v for k, v in value.items() if k not in ignored}
    if clean(context) != clean(saved.get("portfolio_context") or {}):
        raise ValueError("Finish-only recovery cannot change the portfolio, mandate or plays.")
    if payload.get("workflow_version") != 4:
        raise ValueError("Finish-only recovery requires the independent portfolio workflow.")
    for branch in ("independent", "current"):
        if (saved.get("baseline_branches", {}).get(branch) or {}).get("status") != "sealed":
            raise ValueError("Finish-only recovery requires both sealed baseline portfolios.")
    for field in ("independent_ideal", "current_portfolio_assessment", "provisional_recommendation"):
        if not (saved.get(field) or {}).get("asset_class_targets"):
            raise ValueError(f"Finish-only recovery requires saved {field}.")
    reviews = saved.get("analytical_reviews") or []
    expected = {"exposure_equivalence_reviewer", "defensive_regime_reviewer"}
    if {row.get("council_lane") for row in reviews if row.get("stage_status") == "complete"} != expected:
        raise ValueError("Finish-only recovery requires the completed analytical reviews.")
    if not (saved.get("evidence_brief") or {}).get("facts"):
        raise ValueError("Finish-only recovery requires saved source evidence.")
    hashes = {field: digest(saved.get(field)) for field in ("portfolio_context", "portfolio_snapshot",
        "independent_ideal", "current_portfolio_assessment", "investment_plays", "analytical_reviews",
        "provisional_recommendation", "evidence_brief")}
    policy = {"mode": "finish_from_saved_research", "source_run_id": source.name,
        "source_checkpoint_hash": checkpoint_hash(path), "source_checkpoint_hash_scheme": "sha256_file",
        "preserved_input_hashes": hashes,
        "source_checks": "closed_with_limitations", "new_research_allowed": False,
        "new_source_checks_allowed": False, "note": NOTE,
        "source_failed_requests": [{key: row.get(key) for key in ("stage", "model", "status", "failure_type", "error")}
            for row in runtime.previous_receipts if row.get("status") in {"failed", "blocked"}]}
    completed = {row.get("input_hash") or row.get("stage") for row in runtime.previous_receipts
        if row.get("status") == "complete"}
    policy["preserved_completed_checkpoint_entries"] = max(runtime._completed_cache_count(), len(completed))
    policy["preserved_cache_checkpoint"] = str(path)
    # These calls cannot be requested again in finish-only mode. Preserve their
    # immutable checkpoint rather than hydrating and copying all provider output.
    runtime.cache.clear()
    runtime._record_memo.clear()
    archive_only = {"prompt", "request_messages", "raw_response", "retained_output"}
    runtime.previous_receipts = [{key: value for key, value in row.items() if key not in archive_only}
        for row in runtime.previous_receipts]
    runtime.completion_recovery = policy
    runtime.receipts = [{**deepcopy(row), "reused": True, "recovery_scope": "finish_from_saved_research"}
        for row in runtime.previous_receipts if row.get("status") == "complete"]
    # Keep bulky raw research in its immutable source archive, not several in-memory copies.
    archived = sorted(ARCHIVE_FIELDS & saved.keys())
    for key in ARCHIVE_FIELDS:
        saved.pop(key, None)
        runtime.partial.pop(key, None)
    evidence_runs = []
    for row in saved.get("evidence_runs", []):
        brief = row.get("evidence_brief") or {}
        evidence_runs.append({**{key: deepcopy(row[key]) for key in
            ("label", "model", "provider", "error", "supplementary", "stage_status") if key in row},
            "evidence_brief": {key: brief[key] for key in ("stage_error", "stage_status", "evidence_status") if key in brief},
            "source_archive": deepcopy(row.get("source_archive")) or
                {"run_id": source.name, "field": "evidence_runs", "label": row.get("label")}})
    saved["evidence_runs"] = evidence_runs
    saved["preserved_research_archive"] = {"source_run_id": source.name, "source_checkpoint": str(path),
        "fields": [*archived, "evidence_runs"], "source_checkpoint_hash": policy["source_checkpoint_hash"],
        "parent_archive": saved.get("preserved_research_archive")}
    excluded = {"funding", "pipeline_error", "analysis_health", "execution_progress", "stage_receipts", "work_plan"}
    runtime.partial.update({key: deepcopy(value) for key, value in saved.items() if key not in excluded})
    runtime.partial.update(pipeline_status="running", completion_recovery=policy)
    return {**deepcopy(saved), "resume_boundary": "finish_from_saved_research", "source_run_id": source.name,
        "source_checkpoint_hash": policy["source_checkpoint_hash"], "research_cutoff": payload.get("research_cutoff"),
        "baseline_hashes": {field: hashes[field] for field in ("independent_ideal", "current_portfolio_assessment")}}


async def close_source_checks(evidence, runtime, selected=None, callback=None):
    """Retain actual verdicts; completion of the phase must not certify the claims."""
    result = deepcopy(evidence)
    checks, pending = reusable_fact_checks(result["facts"], result.get("source_packet") or {})
    selected = set(selected or [])
    policy = runtime.completion_recovery
    previously_selected = set(policy.get("selected_fact_ids", []))
    policy["selected_fact_ids"] = sorted(previously_selected | selected)
    policy["retained_check_fact_ids"] = sorted(row["fact_id"] for row in checks)
    policy["unverified_fact_ids"] = sorted(row["id"] for row in pending
        if row["id"] in set(policy["selected_fact_ids"]))
    result["source_check_completion"] = {key: deepcopy(policy[key]) for key in
        ("mode", "note", "retained_check_fact_ids", "unverified_fact_ids")}
    result["research_limitations"] = list(dict.fromkeys([*result.get("research_limitations", []), NOTE]))
    from .portfolio_work import record_work
    await record_work(runtime, "source_checks", status="with_limitations", request_count=0,
        reason=NOTE, retained_checks=len(checks), unverified_selected_facts=len(policy["unverified_fact_ids"]))
    await runtime.aupdate_partial(completion_recovery=policy, evidence_brief=result)
    if callback:
        await callback(result, {row["id"] for row in result["facts"]})
    return result


def retained_details(rows, saved, evidence):
    previous = {row["asset_class"]: row for row in (saved.get("investment_details") or {}).get("asset_class_targets", [])}
    retained = []
    for row in rows:
        old = previous.get(row["asset_class"]) or {}
        if (old.get("detail_status") != "current" or not substantive_details(old)
                or old.get("detail_decision_hash") != detail_basis(row)
                or old.get("detail_evidence_hash") != detail_basis({**row, **old}, evidence)):
            continue
        retained.append(deepcopy(old))
    return retained


def compact_completion_prompt(prompt):
    """Share identical source verdicts without dropping observations or checks."""
    result = deepcopy(prompt)
    table = result.get("evidence_brief", {}).get("observations", {})
    columns = table.get("columns", []) if isinstance(table, dict) else []
    if "source_review" not in columns or "source_reviews" in table:
        return result
    index = columns.index("source_review")
    rows = table.get("rows", [])
    encode = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    counts = Counter(encode(row[index]) for row in rows if len(row) > index and isinstance(row[index], dict))
    repeated = {key: "review_" + str(i + 1) for i, key in enumerate(sorted(
        key for key, count in counts.items() if count > 1 and len(key) > 120))}
    if not repeated:
        return result
    table["source_reviews"] = {ref: json.loads(key) for key, ref in repeated.items()}
    table["source_review_encoding"] = (
        "A source_review cell containing source_review_ref uses the exact verdict in source_reviews. "
        "This only shares identical records; unresolved or unsupported verdicts remain unresolved or unsupported.")
    for row in rows:
        if len(row) > index and isinstance(row[index], dict):
            reference = repeated.get(encode(row[index]))
            if reference:
                row[index] = {"source_review_ref": reference}
    return result


def mark_completion_artifact(artifact, runtime):
    policy = getattr(runtime, "completion_recovery", None)
    if not policy:
        return artifact
    artifact["completion_recovery"] = deepcopy(policy)
    artifact.setdefault("provenance", {}).update(recovery_scope="finish_from_saved_research",
        source_run_id=policy["source_run_id"])
    artifact["structured_data"]["source_check_completion"] = {
        key: deepcopy(policy.get(key)) for key in ("mode", "note", "retained_check_fact_ids", "unverified_fact_ids", "additional_model_review")}
    for field in ("analyst_memo_markdown", "chairman_memo_markdown"):
        artifact[field] = artifact.get(field, "").rstrip() + "\n\n### Source-check qualification\n\n" + NOTE + "\n"
        if policy.get("additional_model_review") == "not_run":
            artifact[field] += "The saved analytical reviews were retained; no additional model consistency review was run.\n"
    runtime.partial.update(artifact)
    return artifact
