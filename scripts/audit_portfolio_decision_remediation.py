"""Offline regression audit of a saved run. Never calls providers or modifies it."""

import argparse
import json
from copy import deepcopy
from pathlib import Path

from backend.portfolio_evidence import merge_briefs
from backend.portfolio_judgment import linked_facts
from backend.portfolio_runtime import digest, load_record, unsupported_response_format, write_json_atomic


def audit(path):
    original = json.loads(path.read_text())
    before = digest(original)
    evidence = original.get("evidence_brief") or {}
    proposal = original.get("macro_positioning") or {}
    known = {fact["id"] for fact in evidence.get("facts", [])}
    receipts, missing_records = [], []
    for row in original.get("stage_receipts", []):
        try:
            receipts.append(load_record(path.parent, row))
        except FileNotFoundError:
            receipts.append(row)
            missing_records.append(row.get("stage"))
    format_errors = [row for row in receipts if unsupported_response_format(row.get("raw_response") or row)]
    refreshed = deepcopy(evidence)
    for fact in refreshed.get("facts", []):
        fact["source_digest"] = "regression-test-source-refresh"
    merged = merge_briefs([evidence, refreshed])
    merged_ids = {fact["id"] for fact in merged["facts"]}
    reviews = original.get("analytical_reviews") or []
    result = {"source_run_id": original.get("id") or path.name, "source_hash": before,
        "original": {"fact_count": len(known), "final_missing_fact_ids": sorted(linked_facts(proposal) - known),
            "provider_format_failures": [{"model": row.get("model"), "error": row.get("error")} for row in format_errors],
            "reviewers": [{"role": row.get("council_lane"), "model": row.get("model"), "status": row.get("stage_status")} for row in reviews],
            "play_count": len(original.get("play_assessments") or []),
            "assessed_legs": sum(len(play.get("legs") or []) for play in original.get("play_assessments") or []),
            "brief": (original.get("portfolio_snapshot") or {}).get("mandate") or {}},
        "offline_regressions": {"observation_ids_retained_after_source_refresh": known <= merged_ids,
            "source_artifact_unchanged": digest(json.loads(path.read_text())) == before},
        "audit_limitations": {"raw_records_not_copied_locally": len(missing_records)},
        "interpretation": "This verifies code behaviour against saved inputs. It does not regenerate the memo or establish that new financial conclusions are superior.",
        "requires_bounded_repair": ["Recover the missing substantive reviewer", "Research remaining material play questions",
            "Reconcile and check factual corrections in the final memo", "Compare financial quality and actual cost against the preserved original"]}
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(args.artifact)
    if args.output:
        if args.output.resolve() == args.artifact.resolve():
            raise SystemExit("Audit output must not replace the source memo.")
        write_json_atomic(args.output, report)
    print(json.dumps(report, indent=2))
