"""Offline accounting of the September 22 stopped recovery; no provider calls."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.portfolio_evidence import reusable_fact_checks
from backend.portfolio_independent import material_detail_targets
from backend.portfolio_judgment import linked_facts, resolve_fact_aliases
from backend.portfolio_tasks import allocation_batches, evidence_for_decisions, fact_review_batches


def main():
    folder = ROOT / "outputs/audits/portfolio-r360-review-20260922"
    path = folder / "stopped-recovery.json"
    raw = path.read_bytes()
    run = json.loads(raw)
    original = json.loads((folder / "latest.json").read_text())
    evidence = run["evidence_brief"]
    ideal = run["independent_ideal"]
    current = run["current_portfolio_assessment"]
    provisional = resolve_fact_aliases(run["provisional_recommendation"], evidence)
    reviews = run["analytical_reviews"]
    parts = {"independent": ideal, "current": current, "provisional": provisional, "reviews": reviews}
    refs = {name: linked_facts(value) for name, value in parts.items()}
    selected = set.union(*refs.values())
    facts = evidence_for_decisions(evidence, list(parts.values()))["facts"]
    groups = {g for row in facts if row["id"] in selected and row.get("kind") == "forecast"
              for g in row.get("comparison_groups", [])}
    selected.update(row["id"] for row in facts if row.get("supersedes") or
                    row.get("kind") == "forecast" and set(row.get("comparison_groups", [])) & groups)
    retained, pending = reusable_fact_checks(evidence["facts"], evidence["source_packet"])
    pending = [row for row in pending if row["id"] in selected]
    batches = fact_review_batches(pending, evidence["source_packet"])
    details = material_detail_targets(run["portfolio_snapshot"], provisional, reviews)
    receipts = run["stage_receipts"]
    new = [r for r in receipts if not r.get("reused")]
    unique = {r.get("request_id") or (r.get("input_hash"), r.get("attempt"), r.get("started_at")): r
              for r in new}
    models = [r for r in unique.values() if r.get("request_settings") and r.get("started_at")]
    budget = [r for r in new if r.get("failure_type") == "budget_deferred"]
    def size(value):
        return len(json.dumps(value, ensure_ascii=False).encode())
    def summary(proposal):
        rows = proposal.get("asset_class_targets", [])
        return {"positive_targets": sum((r.get("target_pct") or 0) > 0 for r in rows),
                "total_pct": sum(r.get("target_pct") or 0 for r in rows),
                "executive_summary": proposal.get("executive_summary"),
                "targets": [{k: r.get(k) for k in ("asset_class", "target_pct", "rationale", "fact_ids")}
                            for r in rows]}
    metrics = {
        "artifact": path.name, "artifact_sha256": sha256(raw).hexdigest(), "artifact_bytes": len(raw),
        "stop": {"reason": "user_requested", "signal": "SIGTERM", "worker_pid": 677,
                 "started_at": "2026-09-21T23:49:34Z", "finished_at": "2026-09-22T08:19:54Z",
                 "elapsed_seconds": 30620, "job_status": "failed", "returncode": -15,
                 "worker_absent_verified_at": "2026-09-22T08:20:19.558028Z",
                 "automation_deleted": "finish-deepseek-portfolio-recovery-audit"},
        "saved_pipeline_status": run["pipeline_status"], "checkpoint": run["checkpoint_info"],
        "workload": run["workload"],
        "same_inputs_as_r360": {k: run.get(k) == original.get(k) for k in
                                ("portfolio_context", "portfolio_snapshot", "baseline_branches",
                                 "independent_ideal", "current_portfolio_assessment")},
        "context_differences": sorted(k for k in run["portfolio_context"].keys() | original["portfolio_context"].keys()
                                      if run["portfolio_context"].get(k) != original["portfolio_context"].get(k)),
        "same_plays_as_r360": run["investment_plays"] == original["investment_plays"],
        "original_play_text": [{k: p.get(k) for k in ("id", "title", "thesis", "text")}
                               for p in run["investment_plays"]],
        "play_components": [c.get("name") for p in run["investment_plays"] for c in p.get("components", [])],
        "evidence": {"facts": len(evidence["facts"]), "sources": len(evidence["source_packet"]["sources"]),
                     "claim_status": dict(Counter(r.get("claim_status") for r in evidence["facts"])),
                     "retained_checks": len(retained)},
        "future_source_checks": {"selected_unique_ids": len(selected), "pending_facts": len(pending),
            "batches": len(batches), "sum_batch_bytes": sum(map(size, batches)),
            "largest_batch_bytes": max(map(size, batches), default=0),
            "unique_ids_by_branch": {k: len(v) for k, v in refs.items()},
            "ids_outside_provisional": len(selected - refs["provisional"]),
            "provisional_refs_by_field": {k: len(linked_facts(v)) for k, v in provisional.items()
                                           if linked_facts(v)},
            "review_refs_by_field": {k: len(linked_facts([r.get(k) for r in reviews]))
                                     for k in reviews[0] if linked_facts([r.get(k) for r in reviews])}},
        "future_details": {"sleeves": len(details), "batches": len(allocation_batches(details))},
        "reviews": [{k: r.get(k) for k in ("council_lane", "model", "models", "review_completion",
                    "completed_review_parts", "total_review_parts")} | {
                    "findings": len(r.get("findings", [])), "questions": len(r.get("market_questions", [])),
                    "scenarios": len(r.get("scenario_risks", []))} for r in reviews],
        "model_records": {"new_indexed_records": len(models),
            "status": dict(Counter(r.get("status") for r in models)),
            "failure_type": dict(Counter(r.get("failure_type") for r in models if r.get("status") == "failed")),
            "input_tokens_reported": sum((r.get("usage") or {}).get("prompt_tokens", 0) or 0 for r in models),
            "output_tokens_reported": sum((r.get("usage") or {}).get("completion_tokens", 0) or 0 for r in models)},
        "budget_deferred": [{k: r.get(k) for k in ("stage", "started_at", "error", "request_id")}
                            for r in budget],
        "provisional": summary(provisional), "plays": provisional.get("play_assessments", []),
        "comparison_issues": provisional.get("comparison_issues"),
        "phases": run["execution_progress"]["phases"],
        "unfinished_tasks_at_last_snapshot": [{k: row.get(k) for k in
            ("label", "cache_key", "status", "provider_request_id", "started_at")}
            for row in run["execution_progress"]["active_requests"]],
        "absent_final_fields": [k for k in ("macro_positioning", "allocator_commentary", "final_consistency_review")
                                if not run.get(k)],
    }
    # Emit new audit products only; never rewrite either saved run.
    (folder / "stopped-recovery-audit.json").write_text(json.dumps(metrics, indent=2) + "\n")
    (folder / "stopped-provisional.json").write_text(json.dumps(provisional, indent=2) + "\n")
    assert sha256(path.read_bytes()).hexdigest() == metrics["artifact_sha256"]
    print(json.dumps({k: v for k, v in metrics.items() if k not in
                      {"provisional", "plays", "phases", "original_play_text", "budget_deferred"}}, indent=2))


if __name__ == "__main__":
    main()
