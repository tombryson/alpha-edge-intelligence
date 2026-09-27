"""Offline request-construction benchmark. Never invokes a model or research provider."""

import argparse
import json
from pathlib import Path

from backend.portfolio_tasks import allocation_batches, allocation_context, evidence_for_decisions, investment_details, investment_evidence
from backend.portfolio_independent import material_detail_targets, reconciliation_prompt, review_prompt_batches
from backend.portfolio_judgment import decision_checks
from backend.portfolio_runtime import digest


def size(value):
    return len(json.dumps(value, ensure_ascii=False).encode())


def benchmark(run, profile=None):
    before = digest(run)
    evidence, snapshot = run["evidence_brief"], run["portfolio_snapshot"]
    provisional, final = run["provisional_recommendation"], run["macro_positioning"]
    ideal, current, reviews = run["independent_ideal"], run["current_portfolio_assessment"], run["analytical_reviews"]
    neutral, plays = run["independent_research_context"], run["investment_plays"]
    records = (profile or {}).get("records", [])
    old_final = next((row for row in records if row["stage"].startswith("final_allocation:") and row["status"] == "complete"), {})
    prompt = reconciliation_prompt(evidence, neutral, ideal, current, snapshot, plays, reviews,
        provisional=provisional, details=run["investment_details"], decision_checks=decision_checks(snapshot, provisional, reviews, evidence))
    original_packet = investment_evidence(evidence)
    detail_rows = material_detail_targets(snapshot, provisional, reviews)
    details = []
    for index, rows in enumerate(allocation_batches(detail_rows)):
        packet = evidence_for_decisions(evidence, rows)
        old = next((row for row in records if row["stage"].startswith("investment_cases:")
                    and row["stage"].endswith(f"investment details {index + 1}") and row["status"] == "complete"), {})
        details.append({"batch": index + 1, "assigned_assets": [row["asset_class"] for row in rows],
            "facts": len(packet["facts"]), "questions": len(packet["research_questions"]), "sources": len(packet["sources"]),
            "evidence_bytes": size(packet), "previous_evidence_bytes": old.get("fields", {}).get("evidence_brief"),
            "allocation_context_bytes": size(allocation_context(provisional)),
            "previous_allocation_context_bytes": old.get("fields", {}).get("recorded_allocation")})
    reviewer = review_prompt_batches("defensive_regime_reviewer", evidence, neutral, ideal, current, snapshot, plays)
    report = {"run_id": run.get("id"), "method": "Reconstruct requests from the saved final evidence. No paid call; byte sizes are not token or cost forecasts. Provisional comparisons use the final ledger as a conservative retrospective test.",
        "archive": {"facts": len(evidence["facts"]), "sources": len(evidence["source_packet"]["sources"]),
            "questions": len(evidence.get("research_questions", [])), "projection_idempotent": investment_evidence(original_packet) == original_packet},
        "provisional_detail_batches": details,
        "investment_details": {"before_bytes": size(run["investment_details"]), "after_bytes": size(investment_details(run["investment_details"]))},
        "final_reconciliation": {"before_bytes": old_final.get("prompt_bytes"), "after_bytes": size(prompt),
            "fields": {key: size(value) for key, value in prompt.items()}, "output_contract": prompt.get("update_contract")},
        "review": {"parts": len(reviewer), "part_bytes": [size(row) for row in reviewer],
            "cumulative_prior_sections": any("earlier_review_sections" in row for row in reviewer)},
        "individual_final_cases": [{"asset_class": row["asset_class"], "evidence_bytes": size(evidence_for_decisions(evidence, [row]))}
                                   for row in final["asset_class_targets"]]}
    assert before == digest(run), "Offline audit mutated the saved run"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = benchmark(json.loads(args.run.read_text()), json.loads(args.profile.read_text()) if args.profile else None)
    rendered = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered)


if __name__ == "__main__":
    main()
