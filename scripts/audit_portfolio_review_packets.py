"""Read-only review-packet benchmark; no model calls or changes to saved runs."""

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.portfolio_independent import review_prompt_batches
from backend.portfolio_requests import observation_brief, expand_observations
from backend.portfolio_runtime import digest


def size(value):
    return len(json.dumps(value, ensure_ascii=False).encode())


def benchmark(artifact):
    before = digest(artifact)
    parts = review_prompt_batches("defensive_regime_reviewer", artifact["evidence_brief"],
        artifact["independent_research_context"], artifact["independent_ideal"],
        artifact["current_portfolio_assessment"], artifact["portfolio_snapshot"], artifact["investment_plays"])
    rows = []
    for index, part in enumerate(parts):
        evidence = part["evidence_brief"]
        compact = {key: deepcopy(value) for key, value in evidence.items() if key != "facts"}
        compact.update(observation_brief(evidence))
        restored = expand_observations(compact)
        clean = lambda row: {key: value for key, value in row.items() if value is not None}
        assert [clean(row) for row in restored["facts"]] == [clean(row) for row in evidence["facts"]]
        assert compact.get("other_observations") == evidence.get("other_observations")
        rows.append({"section": index + 1, "case_ids": part["review_scope"]["case_ids"],
            "current_bytes": size(part), "lossless_index_bytes": size({**part, "evidence_brief": compact}),
            "detailed_facts": len(evidence["facts"]), "unique_passages": len(compact["source_passages"]),
            "excerpt_bytes": sum(size(fact.get("source_excerpt")) for fact in evidence["facts"]),
            "unique_excerpt_bytes": size(compact["source_passages"])})
    assert digest(artifact) == before
    current, indexed = sum(row["current_bytes"] for row in rows), sum(row["lossless_index_bytes"] for row in rows)
    return {"run_id": artifact["id"], "original_unchanged": True, "sections_per_reviewer": len(rows),
        "current_bytes": current, "lossless_index_bytes": indexed,
        "byte_reduction_pct": round(100 * (1 - indexed / current), 2),
        "largest_current_bytes": max(row["current_bytes"] for row in rows),
        "largest_indexed_bytes": max(row["lossless_index_bytes"] for row in rows),
        "interpretation": "Representation-only benchmark. Every shown fact and passage is recoverable and discovery entries are retained. It does not fix repeated cases, cross-section inference, large unique evidence or measure live token cost.",
        "sections": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = benchmark(json.loads(args.artifact.read_text()))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "sections"}, indent=2))
