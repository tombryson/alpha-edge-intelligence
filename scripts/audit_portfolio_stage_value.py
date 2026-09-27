"""Offline saved-memo audit; optional request-construction replay, no provider calls."""

import argparse
import hashlib
import json
import re
import time
import tracemalloc
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/audits/portfolio-stage-value-20260923"
FILES = {
    "september23": "outputs/audits/portfolio-finish-comparison-20260923/reader-full.json",
    "september21": "outputs/audits/portfolio-final-review-20260921/latest.json",
    "september20": "outputs/audits/portfolio-deepseek-recovery-review-20260920/latest.json",
    "august11": "outputs/audits/portfolio-20260811/run.json",
}


def timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def group(receipt):
    stage = receipt["stage"]
    prefix, _, task = stage.partition(":")
    if "reviewer" in prefix:
        return "review_archive_lookup" if "source_lookup" in prefix else "financial_review"
    if task == "parallel":
        return "parallel_discovery"
    if task == "citation_source_text":
        return "source_text_retrieval"
    if task.startswith("Extract dated observations"):
        return "observation_extraction"
    if task.startswith("Answer the focused research dimensions"):
        return "question_answers"
    if task.startswith("Review source support"):
        return "source_checks"
    if task.startswith(("Build source-grounded", "Reconcile portfolio evidence")):
        return "evidence_summary"
    if prefix.startswith("research_plan_"):
        return "question_planning"
    return prefix


def union_seconds(intervals):
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(end, merged[-1][1])
        else:
            merged.append([start, end])
    return round(sum(end - start for start, end in merged), 3)


def summarize_receipts(receipts):
    intervals = [(timestamp(r["started_at"]), timestamp(r["finished_at"])) for r in receipts
                 if r.get("started_at") and r.get("finished_at")]
    cost_rows = [r for r in receipts if (r.get("usage") or {}).get("cost") is not None]
    return {
        "receipts": len(receipts), "statuses": dict(Counter(r["status"] for r in receipts)),
        "models": sorted({r["model"] for r in receipts if r.get("model")}),
        "reported_cost_usd": float(sum((Decimal(str(r["usage"]["cost"])) for r in cost_rows), Decimal(0))),
        "receipts_with_cost": len(cost_rows),
        "input_tokens": sum((r.get("usage") or {}).get("prompt_tokens", 0) for r in receipts),
        "output_tokens": sum((r.get("usage") or {}).get("completion_tokens", 0) for r in receipts),
        "first_started_at": min((r["started_at"] for r in receipts if r.get("started_at")), default=None),
        "last_finished_at": max((r["finished_at"] for r in receipts if r.get("finished_at")), default=None),
        "recorded_interval_sum_seconds": round(sum(end - start for start, end in intervals), 3),
        "recorded_interval_union_seconds": union_seconds(intervals),
        "span_seconds": round(max(e for _, e in intervals) - min(s for s, _ in intervals), 3) if intervals else None,
    }


def fact_ids(value):
    return set(re.findall(r"fact_[a-f0-9]{8,}", json.dumps(value)))


def memo_metrics(artifact):
    structured = artifact.get("structured_data") or {}
    final = artifact.get("macro_positioning") or {}
    evidence = artifact.get("evidence_brief") or {}
    text = artifact.get("chairman_memo_markdown") or artifact.get("analyst_memo_markdown") or ""
    main = text.split("## Supporting Research", 1)[0].split("## Sources", 1)[0]
    targets = final.get("asset_class_targets") or []
    questions = evidence.get("research_questions") or []
    reviews = structured.get("analytical_reviews") or []
    findings = [row for review in reviews for row in review.get("findings", [])]
    dispositions = final.get("review_dispositions") or []
    if not dispositions:
        dispositions = (final.get("final_reconciliation") or {}).get("response", {}).get("review_dispositions") or []
    refs = fact_ids(final)
    facts = evidence.get("facts") or []
    return {
        "artifact": artifact.get("file") or artifact.get("id"),
        "mandate": (artifact.get("portfolio_snapshot") or {}).get("mandate"),
        "facts": len(facts), "source_documents": len((evidence.get("source_packet") or {}).get("sources") or []),
        "legacy_citations": len(artifact.get("source_citations") or []),
        "question_statuses": dict(Counter(q.get("status") for q in questions)),
        "final_targets": len(targets), "target_total_pct": sum(r.get("target_pct", 0) or 0 for r in targets),
        "final_fact_references": len(refs),
        "referenced_fact_statuses": dict(Counter(f.get("claim_status") for f in facts if f["id"] in refs)),
        "main_markdown_words": len(main.split()), "all_markdown_words": len(text.split()),
        "findings": len(findings), "finding_kinds": dict(Counter(f.get("kind") for f in findings)),
        "dispositions": len(dispositions), "disposition_statuses": dict(Counter(d.get("status") for d in dispositions)),
        "finding_ids_without_final_disposition": sorted({f["id"] for f in findings} - {d.get("finding_id") for d in dispositions}),
        "investment_cases": sum(bool(r.get("investment_case")) for r in targets),
        "case_horizons_missing": [r["asset_class"] for r in targets if (r.get("investment_case") or {}).get("horizon_months") is None],
        "company_evidence_count": len((artifact.get("portfolio_snapshot") or {}).get("company_evidence") or []),
    }


def replay(artifact):
    """Construct current request views only; no runtime, credentials or model requests."""
    from backend.portfolio_independent import independent_context, review_prompt_batches, reconciliation_prompt
    from backend.portfolio_judgment import common_scenario_comparison, linked_facts
    from backend.portfolio_requests import settlement_inputs
    from backend.portfolio_tasks import evidence_for_decisions

    structured = artifact["structured_data"]
    evidence = artifact["evidence_brief"]
    snapshot = artifact["portfolio_snapshot"]
    neutral = independent_context(snapshot, artifact["provenance"]["research_cutoff"])
    result = {}
    for mode, plays in (("historical_components", artifact["investment_plays"]), ("brief_plays", [])):
        started = time.perf_counter()
        packets = review_prompt_batches("exposure_equivalence_reviewer", evidence, neutral,
            structured["independent_ideal"], structured["current_portfolio_assessment"], snapshot, plays)
        units = [unit for packet in packets for unit in packet.get("review_scope", {}).get("case_ids", [])]
        result[mode] = {"packets_for_one_role": len(packets), "review_units": len(units),
            "standalone_research_units": sum("research_assessment" in u or u.startswith("question.") for u in units),
            "play_units": sum(u.startswith("play.") for u in units),
            "total_prompt_bytes": sum(len(json.dumps(p, ensure_ascii=False).encode()) for p in packets),
            "construction_seconds": round(time.perf_counter() - started, 3)}
    comparison = common_scenario_comparison(snapshot, structured["independent_ideal"], artifact["macro_positioning"], evidence)
    result["current_code_ideal_scenario_unknown_pct"] = [s["directional_weight_pct"]["unknown"]
        for s in comparison["views"]["independent_ideal"]["scenarios"]]
    old_id = "question_ea1ad7f919b766a6e8d7"
    later = next(row for row in evidence["research_questions"] if row.get("reuse_question_id") == old_id)
    packet = evidence_for_decisions(evidence, {"research_question_ids": [old_id]})
    expected = linked_facts(later["answers"])
    assert expected <= {row["id"] for row in packet["facts"]}
    result["answer_continuity"] = {"original_question": old_id, "later_question": later["id"],
        "expected_fact_ids": sorted(expected), "retained_fact_ids": [row["id"] for row in packet["facts"]],
        "original_scope_status": next(row["scope_status"] for row in packet["research_questions"] if row["question_id"] == old_id)}
    provisional, details, reviews = (structured[key] for key in
        ("provisional_recommendation", "investment_details", "analytical_reviews"))
    settled = settlement_inputs(evidence, provisional, details, reviews)
    index = settled["evidence_brief"]["observations"]
    shown = {row[index["columns"].index("id")] for row in index["rows"]}
    assert expected <= shown
    result["settlement_evidence"] = {"facts": len(shown), "json_bytes": len(json.dumps(settled["evidence_brief"], ensure_ascii=False).encode()),
        "later_uranium_citations_retained": len(expected & shown)}
    tracemalloc.start()
    started = time.perf_counter()
    prompt = reconciliation_prompt(evidence, neutral, structured["independent_ideal"],
        structured["current_portfolio_assessment"], snapshot, artifact["investment_plays"], reviews,
        provisional=provisional, details=details, brief_plays=True)
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    result["final_prompt"] = {"json_bytes": len(json.dumps(prompt, ensure_ascii=False).encode()),
        "construction_seconds": round(elapsed, 3), "peak_python_bytes": peak,
        "measurement_scope": "Request construction allocations after loading the archive, not full worker RSS"}
    result["caveat"] = "Same final saved archive used in both constructions, not a prediction of a new run's pre-review evidence or paid call count."
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", action="store_true", help="Also build current review requests offline")
    parser.add_argument("--output", type=Path, default=OUT, help="Keep implementation replays separate from the original audit")
    args = parser.parse_args()
    artifacts, hashes = {}, {}
    for name, relative in FILES.items():
        data = (ROOT / relative).read_bytes()
        hashes[relative] = hashlib.sha256(data).hexdigest()
        artifacts[name] = json.loads(data)
    latest = artifacts["september23"]
    receipts = latest["stage_receipts"]
    ids = [r["request_id"] for r in receipts if r.get("request_id")]
    assert len(ids) == len(set(ids)), "Deduplicate provider IDs before reporting lineage costs"
    groups = defaultdict(list)
    for receipt in receipts:
        groups[group(receipt)].append(receipt)
    stage_metrics = {name: summarize_receipts(rows) for name, rows in groups.items()}
    summary = summarize_receipts(receipts)
    # Intervals can contain provider polling/retries/local work; not pure billable compute.
    summary["no_recorded_active_request_seconds"] = round(summary["span_seconds"] - summary["recorded_interval_union_seconds"], 3)
    new_receipts = [r for r in receipts if not r.get("reused")]
    usage_missing = [r for r in receipts if r["status"] == "complete" and (r.get("usage") or {}).get("cost") is None]
    cases = {}
    for name, artifact in artifacts.items():
        final = artifact.get("macro_positioning") or {}
        cases[name] = {r["asset_class"]: {key: r.get(key) for key in
            ("target_pct", "rationale", "investment_case", "baseline_links", "action_basis", "research_gaps")}
            for r in final.get("asset_class_targets", []) if any(word in r["asset_class"].lower()
                for word in ("energy", "gold", "silver", "uranium", "treasur", "bond", "equities"))}
    reviews = latest["structured_data"]["analytical_reviews"]
    corrections = [{"role": review["council_lane"], **finding} for review in reviews
                   for finding in review.get("findings", []) if finding.get("kind") == "factual_correction"]
    report = {
        "scope": "Saved receipt lineage, not an invoice, fresh-run benchmark or current production configuration",
        "input_sha256": hashes,
        "lineage": summary, "finish_only_receipts": summarize_receipts(new_receipts),
        "unique_provider_ids": len(ids),
        "completed_without_reported_cost": dict(Counter(group(r) for r in usage_missing)),
        "stages": stage_metrics,
        "memos": {name: memo_metrics(a) for name, a in artifacts.items()},
        "top_ten_inputs": [{key: r.get(key) for key in ("stage", "model", "usage", "record_ref", "reused")}
                           for r in sorted(receipts, key=lambda r: (r.get("usage") or {}).get("prompt_tokens", 0), reverse=True)[:10]],
        "source_check_completion": {key: len(value) if isinstance(value, list) else value
            for key, value in latest["structured_data"]["source_check_completion"].items()},
        "scenario_unknown_pct": {name: [s["directional_weight_pct"]["unknown"] for s in row["scenarios"]]
            for name, row in latest["macro_positioning"]["common_scenario_comparison"]["views"].items()},
    }
    if args.replay:
        report["offline_replay"] = replay(latest)
    for relative, sha in hashes.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == sha
    args.output.mkdir(parents=True, exist_ok=True)
    for name, value in (("metrics.json", report), ("case-evidence.json", cases), ("review-corrections.json", corrections)):
        (args.output / name).write_text(json.dumps(value, indent=2, ensure_ascii=False))
    table = ["| Stage | Complete / failed | Reported USD | Input tokens | Request-span min | Active-interval min |",
             "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for name, value in sorted(stage_metrics.items(), key=lambda item: item[1]["first_started_at"] or ""):
        cost = f"{value['reported_cost_usd']:.4f}" if value["receipts_with_cost"] else "Not reported"
        table.append(f"| {name} | {value['statuses'].get('complete', 0)} / {value['statuses'].get('failed', 0)} | "
            f"{cost} | {value['input_tokens']:,} | {value['span_seconds'] / 60:.1f} | "
            f"{value['recorded_interval_union_seconds'] / 60:.1f} |")
    (args.output / "stages.md").write_text("\n".join(table) + "\n")
    print(json.dumps({"lineage": summary, "finish_only": report["finish_only_receipts"],
        "offline_replay": report.get("offline_replay"), "source_check_completion": report["source_check_completion"]}, indent=2))


if __name__ == "__main__":
    main()
