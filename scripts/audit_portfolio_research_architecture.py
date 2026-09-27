"""Offline counterexamples for the September 23 research-architecture review.

These are diagnostic probes, not acceptance tests or financial conclusions.
Provider responses are synthetic; no network or production writes are allowed.
"""

import argparse
import asyncio
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.portfolio_exposures import economic_case_aliases
from backend.portfolio_evidence import apply_fact_checks, review_fields
from backend.portfolio_research import coverage, normalize_questions, remaining_search
from backend.portfolio_runtime import CURRENT_RUNTIME, PortfolioRuntime, write_json_atomic
from backend.portfolio_tasks import evidence_for_decisions
from scripts import portfolio_positioning_memo as memo


def question():
    return {"question": "What do primary releases establish about regional oil exports?",
        "topic": "oil", "economic_question": "exports", "geography": "Gulf",
        "period": "September 2026", "horizon": "12 months",
        "required_dimensions": ["export volumes"], "status": "unanswered",
        "material_reason": "Export availability changes the supply premise",
        "reuse_assessment": "Price observations do not establish physical exports",
        "asset_classes": ["oil_producers"], "decision_impact": "high", "critical_premise": True}


def evidence():
    return {"evidence_status": "complete", "facts": [], "source_packet": {
        "as_of": "2026-09-23T00:00:00Z", "sources": [{"id": "primary",
        "url": "https://example.org/release", "excerpt": "Exports remain uncertain.",
        "published_at": "2026-09-22"}]}}


async def retrieval_probe():
    queries, structured = [], []

    class Provider:
        model = "ultra2x"

        async def gather(self, runtime, **kwargs):
            queries.append(kwargs["question"])
            return {"provider": "parallel", "question_status": "partial",
                "results": [{"url": f"https://example.org/release-{len(queries)}", "content": f"Source packet {len(queries)}: exports remain uncertain."}],
                "expansion_query": "What does the port authority's September loading register report?"}

    async def structure(lane, **kwargs):
        structured.append({"query": lane["query"], "inspection": bool(lane.get("source_inspection"))})
        lane["evidence_brief"] = evidence()
        return lane

    with tempfile.TemporaryDirectory() as directory, patch.object(memo, "ParallelSourceProvider", Provider), \
            patch.object(memo, "_structure_evidence_lane", structure), \
            patch.dict("os.environ", {"PORTFOLIO_RESEARCH_BUDGET_USD": "3", "PORTFOLIO_FOLLOWUP_TASK_PRICE_USD": "0.6"}):
        runtime = PortfolioRuntime(Path(directory) / "audit.json")
        token = CURRENT_RUNTIME.set(runtime)
        try:
            brief, runs, report = await memo._run_question_research(evidence(), "deep", {
                "phase": "independent", "questions": [question()]})
            first_pass = {"provider_queries": list(queries), "structured_queries": deepcopy(structured),
                "recorded_lanes": len(runs), "answered": report["answered"],
                "same_source_packet": runs[0]["parallel"] == runs[-1]["parallel"]}
            # A newly supplied primary document should be eligible for inspection.
            brief["source_packet"]["sources"].append({"id": "new_primary", "url": "https://example.org/new-release",
                "excerpt": "New dated export table", "published_at": "2026-09-22"})
            followup = {**question(), "inspect_source_ids": ["new_primary"]}
            _, later, later_report = await memo._run_question_research(brief, "deep", {
                "phase": "current", "questions": [followup]})
            return {"expansion": first_pass, "new_document": {"new_lanes": len(later),
                "new_document_inspections": sum(row["inspection"] for row in structured),
                "status": later_report["questions"][0]["status"],
                "retrieval_status": later_report["questions"][0].get("retrieval_status"),
                "reason": later_report["questions"][0].get("reason"),
                "remaining_search": remaining_search(later_report["questions"][0])}}
        finally:
            CURRENT_RUNTIME.reset(token)


def conflicting_answer_probe():
    brief = evidence()
    brief["facts"] = [{"id": name, "kind": "forecast", "observation_type": "forecast",
        "metric": "September net export change", "value": value,
        "unit": "million barrels/day", "benchmark": "Gulf", "source_ids": [name],
        "currency": "not_applicable", "vintage": "2026-09-22", "target_period": "September 2026",
        "observed_at": "2026-09-22", "published_at": "2026-09-22",
        "source_excerpt": f"September Gulf net export change forecast: {value} million barrels/day."}
        for name, value in [("increase", 2), ("decrease", -2)]]
    brief["source_packet"]["sources"] = [{"id": fact["id"], "url": "https://example.org/" + fact["id"],
        "published_at": "2026-09-22", "excerpt": fact["source_excerpt"]} for fact in brief["facts"]]
    brief["facts"] = apply_fact_checks(brief["facts"], [{"fact_id": fact["id"],
        "checks": {key: "supported" for key in review_fields(fact)},
        "reason": "Synthetic source-support fixture; these two forecasts disagree."} for fact in brief["facts"]],
        brief["source_packet"])
    row = normalize_questions([question()], brief)[0]
    answers = [{"dimension": "export volumes", "status": "answered", "answer": text, "fact_ids": [name]}
        for name, text in [("increase", "The forecast projects an export increase of 2 million barrels/day."),
                           ("decrease", "The forecast projects an export decrease of 2 million barrels/day.")]]
    forward = coverage(row, brief, answers)
    reverse = coverage(row, brief, list(reversed(answers)))
    return {"forward": forward, "reversed": reverse,
        "order_changes_selected_facts": forward["answers"][0]["fact_ids"] != reverse["answers"][0]["fact_ids"]}


def alias_probe():
    brief = evidence()
    brief["facts"] = [{"id": "contrary", "metric": "Gold opportunity cost", "value": "rising",
        "source_ids": ["primary"], "research_question_ids": ["gold_question"]}]
    brief["research_questions"] = [{"id": "gold_question", "question": "How have real yields changed?",
        "asset_classes": ["BULLION"], "status": "answered", "answers": [{"dimension": "real yields",
        "answer": "Opportunity cost rose.", "status": "answered", "fact_ids": ["contrary"]}]}]
    ideal = {"asset_class_targets": [{"asset_class": "BULLION", "target_pct": 10}]}
    target = {"asset_class": "GOLD_ETF", "aliases": ["BULLION"], "target_pct": 10}
    current = {"asset_class_targets": [target]}
    aliases = economic_case_aliases(ideal, current, {})
    selected = evidence_for_decisions(brief, target)
    explicit_link = evidence_for_decisions(brief, {**target, "research_question_ids": ["gold_question"]})
    return {"declared_equivalence": aliases, "facts_from_alias_only": [row["id"] for row in selected["facts"]],
        "facts_with_explicit_question_link": [row["id"] for row in explicit_link["facts"]]}


def artifact_inventory(path):
    raw = path.read_bytes()
    data = json.loads(raw)
    brief = data.get("evidence_brief", {})
    facts = brief.get("facts", [])
    sources = brief.get("source_packet", {}).get("sources", [])
    questions = brief.get("research_questions", [])
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
        "workflow_version": data.get("workflow_version"), "facts": len(facts), "sources": len(sources),
        "questions": len(questions), "question_status": dict(Counter(row.get("status", "missing") for row in questions)),
        "searched_but_unanswered": sum(row.get("status") != "answered" and bool(row.get("searched_dimensions")) for row in questions),
        "fact_kinds": dict(Counter(row.get("kind", "missing") for row in facts)),
        "typed_observations": sum(bool(row.get("observation_type")) for row in facts),
        "available_at_recorded": sum(bool(row.get("available_at")) for row in facts),
        "origin_release_id_recorded": sum(bool(row.get("origin_release_id")) for row in sources),
        "source_context_coverage": dict(Counter(row.get("context_coverage", "unrecorded") for row in sources))}


async def main(args):
    def no_network(*args, **kwargs):
        raise AssertionError("This audit cannot access the network")

    with patch.object(httpx.AsyncClient, "send", no_network), patch.object(httpx.Client, "send", no_network):
        result = {"scope": "Synthetic offline counterexamples; not production incidence or financial truth",
            "retrieval": await retrieval_probe(), "answer_order": conflicting_answer_probe(), "alias_scope": alias_probe()}
    if args.artifact:
        result["historical_inventory"] = artifact_inventory(args.artifact)
    if args.output:
        write_json_atomic(args.output, result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--output", type=Path)
    asyncio.run(main(parser.parse_args()))
