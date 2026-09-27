"""Replay source-check selection/packing offline; no provider calls or artifact mutation."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.portfolio_runtime import digest
from backend.portfolio_tasks import decision_source_check_plan, fact_review_batches


def old_batches(facts, packet):
    result = []
    for offset in range(0, len(facts), 8):
        rows = facts[offset:offset + 8]
        refs = {ref for row in rows for ref in row.get("source_ids", [])}
        result.append({"facts": rows, "source_packet": {"as_of": packet.get("as_of"),
            "sources": [source for source in packet.get("sources", []) if source["id"] in refs]}})
    return result


def metrics(batches):
    sizes = [len(json.dumps(batch).encode()) for batch in batches]
    return {"calls_before_cache_reuse": len(batches), "payload_bytes": sum(sizes),
        "largest_payload_bytes": max(sizes, default=0),
        "source_occurrences": sum(len(batch["source_packet"]["sources"]) for batch in batches),
        "fact_counts": [len(batch["facts"]) for batch in batches]}


def benchmark(artifact):
    before = digest(artifact)
    evidence = artifact["evidence_brief"]
    packet = evidence["source_packet"]
    old = artifact["source_check_plan"]
    new = decision_source_check_plan(evidence, artifact["provisional_recommendation"], artifact["analytical_reviews"])
    old_facts = [row for row in evidence["facts"] if row["id"] in old["fact_ids"]]
    new_facts = [row for row in evidence["facts"] if row["id"] in new["fact_ids"]]
    direct = {ref for ref, reasons in old["selection_reasons"].items()
              if any(reason == "decision_or_alternative" or reason.startswith("factual_challenge:") for reason in reasons)}
    assert direct <= set(new["fact_ids"]) | set(new["missing_fact_ids"])
    grouped = fact_review_batches(new_facts, packet)
    assert sorted(row["id"] for batch in grouped for row in batch["facts"]) == sorted(new["fact_ids"])
    for batch in grouped:
        refs = {ref for row in batch["facts"] for ref in row.get("source_ids", [])}
        assert batch["source_packet"]["sources"] == [source for ref in dict.fromkeys(
            ref for row in batch["facts"] for ref in row.get("source_ids", []))
            for source in packet.get("sources", []) if source["id"] == ref]
        assert {source["id"] for source in batch["source_packet"]["sources"]} <= refs
    previous = metrics(old_batches(old_facts, packet))
    current = metrics(grouped)
    assert before == digest(artifact)
    return {"run_id": artifact.get("id"), "original_unchanged": True,
        "archive_facts": len(evidence["facts"]), "direct_and_challenged_facts": len(direct),
        "all_direct_and_challenged_facts_retained": True,
        "previous_selected_facts": len(old_facts), "selected_facts": len(new_facts),
        "previous": previous, "selection_only": metrics(old_batches(new_facts, packet)), "streamlined": current,
        "call_reduction_pct": round(100 * (1 - current["calls_before_cache_reuse"] / previous["calls_before_cache_reuse"]), 2),
        "payload_reduction_pct": round(100 * (1 - current["payload_bytes"] / previous["payload_bytes"]), 2),
        "scope": "Offline selection and complete JSON payloads, before cache reuse. Not measured provider tokens, cost, quality or wall time.",
        "selection": new}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = benchmark(json.loads(args.artifact.read_text()))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "selection"}, indent=2))
