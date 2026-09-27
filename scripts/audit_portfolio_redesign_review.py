"""Offline second-pass audit of current request builders against a saved portfolio.

Evaluates trusted repository prompt expressions, never the pipeline or a provider.
Saved financial decisions are fixed inputs, not newly generated model outputs.
"""

import argparse
import ast
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

from backend import portfolio_independent as independent
from backend import portfolio_judgment as judgment
from backend import portfolio_tasks as tasks
from backend import portfolio_research as research
from backend import portfolio_requests as requests
from backend.portfolio_runtime import business_data, digest
from scripts import portfolio_positioning_memo as memo


def size(value):
    return len(json.dumps(value, ensure_ascii=False).encode())


def describe(prompt):
    prompt = business_data(prompt)
    packet = prompt.get("evidence_brief") or {}
    strings = Counter()
    def visit(value):
        if isinstance(value, dict):
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
        elif isinstance(value, str) and len(value.encode()) >= 120:
            strings[value] += 1
    visit(prompt)
    return {"bytes": size(prompt), "fields": {key: size(value) for key, value in prompt.items()},
            "facts": len(packet.get("facts", (packet.get("observations") or {}).get("rows", []))), "questions": len(packet.get("research_questions", prompt.get("research_registry", []))),
            "sources": len(packet.get("sources", [])),
            "repeated_long_string_bytes": sum(len(value.encode()) * (count - 1) for value, count in strings.items())}


def prompt_expressions():
    tree = ast.parse(Path(memo.__file__).read_text())
    function = next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef)
                    and node.name == "_run_independent_pipeline")
    result = {}
    for node in ast.walk(function):
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "consistency_request"
                                              for target in node.targets):
            result["decision_consistency"] = node.value
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "call"
                and len(node.args) >= 3 and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[2], ast.Dict)):
            result[node.args[0].value] = node.args[2]
    return result


def audit(run):
    original = digest(run)
    evidence = run["evidence_brief"]
    snapshot = run["portfolio_snapshot"]
    neutral = run["independent_research_context"]
    ideal = run["independent_ideal"]
    current = run["current_portfolio_assessment"]
    plays = run["investment_plays"]
    reviews = run["analytical_reviews"]
    provisional = run["provisional_recommendation"]
    final = deepcopy(run["macro_positioning"])
    final.update(judgment.decision_checks(snapshot, final, reviews, evidence))
    commentary = run.get("allocator_commentary", {})
    stages = {}
    for role in ("exposure_equivalence_reviewer", "defensive_regime_reviewer"):
        parts = independent.review_prompt_batches(role, evidence, neutral, ideal, current, snapshot, plays)
        stages[role] = [describe(part) for part in parts]
    review_parts = independent.review_prompt_batches("defensive_regime_reviewer", evidence, neutral, ideal, current, snapshot, plays)
    for name, old in (("independent_ideal", ideal), ("current_assessment", current)):
        expected = {row["asset_class"] for row in old["asset_class_targets"]}
        covered = {row["asset_class"] for part in review_parts for row in part[name]["asset_class_targets"]}
        stages[name + "_review_coverage"] = {"target_count": len(expected), "omitted_target_ids": sorted(expected - covered),
            "original_current_assessment_rows": len(old.get("current_assessment", [])),
            "included_current_assessment_rows": sum(len(part[name].get("current_assessment", [])) for part in review_parts)}
    stages["provisional"] = describe(independent.reconciliation_prompt(evidence, neutral, ideal, current, snapshot, plays, reviews))
    final_prompt = independent.reconciliation_prompt(evidence, neutral, ideal, current, snapshot, plays, reviews,
        provisional=provisional, details=run["investment_details"],
        decision_checks=judgment.decision_checks(snapshot, provisional, reviews, evidence))
    stages["final_reconciliation"] = describe(final_prompt)
    namespace = {**vars(memo), **vars(tasks), **vars(judgment), **vars(independent), **vars(requests),
        "evidence": evidence, "snapshot": snapshot, "neutral": neutral, "ideal": ideal, "current": current,
        "plays": plays, "reviews": reviews, "final": final, "commentary": commentary,
        "runtime": SimpleNamespace(started_at=neutral["research_cutoff"]),
        "review_document": {**independent.decision_document(final), "commentary": commentary}}
    expressions = prompt_expressions()
    def build(name):
        return eval(compile(ast.Expression(expressions[name]), memo.__file__, "eval"), namespace)
    stages["memo_commentary"] = describe(build("memo_commentary"))
    consistency = build("decision_consistency")
    stages["decision_consistency_not_reached_in_saved_run"] = describe(consistency)
    # A one-exposure hypothetical correction demonstrates the actual dispatch builder's scope.
    namespace.update(consistency= {"decision_revisions": [{"asset_classes": [final["asset_class_targets"][0]["asset_class"]]}]},
        scope={"asset_classes": [final["asset_class_targets"][0]["asset_class"]], "funding_asset_classes": []},
        consistency_request=consistency)
    stages["hypothetical_single_exposure_reconsideration"] = describe(build("decision_reconsideration"))
    stages["settled_decision_consistency_not_reached_in_saved_run"] = describe(build("settled_decision_consistency"))
    # Planner probes use the same final ledger so these are not phase-matched historical savings.
    stages["planner_final_ledger_probe"] = describe(research.planning_prompt("challenge", evidence, neutral))
    clean_packet = tasks.evidence_for_decisions(evidence, [independent.decision_document(final), independent.review_cases(reviews)])
    raw_packet = tasks.evidence_for_decisions(evidence, [final, reviews])
    scopes = {"raw_final_and_reviews": {"bytes": size(raw_packet), "facts": len(raw_packet["facts"]), "questions": len(raw_packet["research_questions"])},
              "decision_document_and_reviews": {"bytes": size(clean_packet), "facts": len(clean_packet["facts"]), "questions": len(clean_packet["research_questions"])}}
    material = independent.material_detail_targets(snapshot, provisional, reviews)
    target_context = {"full_provisional_target_count": len(provisional["asset_class_targets"]),
        "historical_material_context_target_count": len(material),
        "historical_material_context_weight_pct": sum(row.get("target_pct", 0) for row in material),
        "current_recorded_context_target_count": len(tasks.allocation_context(provisional)),
        "current_recorded_context_weight_pct": sum(row.get("target_pct", 0) for row in tasks.allocation_context(provisional)),
        "previous_benchmark_context_bytes": size(tasks.allocation_context(provisional)),
        "historical_material_context_bytes": size(tasks.allocation_context({"asset_class_targets": material}))}
    question_keys = {"oil_commercial_inventories_days_cover", "oil-commercial-inventory-level-and-days-of-cover",
                     "oecd-commercial-oil-inventories-and-days-of-cover"}
    registry, inventory = {}, []
    for original_question in evidence["research_questions"]:
        if original_question.get("economic_question") not in question_keys:
            continue
        row = research.normalize_questions([original_question], evidence)[0]
        matched = research.matching_question(row, registry)
        inventory.append({field: original_question.get(field) for field in ("economic_question", "geography", "period", "horizon")}
            | {"new_id": row["id"], "matched_prior": matched.get("id") if matched else None})
        registry[row["id"]] = row
    schema = independent.reconciliation_prompt(evidence, neutral, ideal, current, snapshot, plays, reviews)["required_schema"]
    assert digest(run) == original, "Audit changed the saved artifact"
    return {"run_id": run.get("id"), "method": "Current trusted request expressions, fixed saved final evidence and decisions. No paid calls. Bytes are not tokens. Provisional/review/planner probes use later evidence; no end-to-end speedup or spend claim.",
        "commentary_in_saved_artifact_bytes": size(commentary),
        "limitations": ["The saved artifact has no persisted completed commentary, although its historical receipt profile records a completed commentary call. Consistency sizes exclude that missing prose.",
            "New reviewer and allocator responses have not been generated. Replaying old decisions measures current construction, not future model behavior.",
            "The single-exposure reconsideration is hypothetical and intentionally isolates whether its scope changes its evidence request."],
        "stages": stages, "raw_vs_clean_scope": scopes, "detail_context": target_context,
        "original_inventory_questions_replayed": inventory,
        "current_provisional_schema": {"fields": list(schema),
            "smaller_alternative_target_fields": list(schema["smaller_change_alternative"]["asset_class_targets"][0])},
        "archive_unchanged": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(json.loads(args.run.read_text()))
    rendered = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered)


if __name__ == "__main__":
    main()
