"""Offline counterexamples for the 2026-09-21 uplift review. No provider calls."""

import asyncio
from copy import deepcopy
import json
from unittest.mock import AsyncMock, patch

from backend.portfolio_decisions import evaluate_conditions, funding_ledger
from backend.portfolio_evidence import FACT_FIELDS, apply_fact_checks, fact_observation_is_supported, merge_briefs
from backend.portfolio_independent import decision_document, establish_play_components
from backend.portfolio_judgment import apply_claim_patches, implementation_comparison
from backend.portfolio_research import complete_component_plan
from backend.portfolio_runtime import CURRENT_RUNTIME, PortfolioRuntime
from scripts import portfolio_positioning_memo as memo


def source_case():
    packet = {"as_of": "2026-09-21T02:00:00Z", "sources": [{"id": "s",
        "url": "https://example.test/report.pdf", "excerpt": "Brent annual 82.6, August 90.9.",
        "published_at": "2026-09-01"}]}
    fact = {"id": "fact_11111111111111111111", "kind": "market_price", "metric": "Brent",
        "value": 82.6, "unit": "USD/bbl", "currency": "USD", "benchmark": "Brent",
        "observed_at": "2026-08-01", "published_at": "2026-09-01", "vintage": "2026",
        "source_ids": ["s"], "source_excerpt": packet["sources"][0]["excerpt"]}
    return packet, fact


async def audit():
    results = []

    def record(identifier, name, expected, observed, passed):
        results.append({"id": identifier, "name": name, "expected": expected,
                        "observed": observed, "passed": bool(passed)})

    packet, fact = source_case()
    fact.update(kind="observed_macro", observation_type="period_statistic", observed_at=None,
                reference_period="Q3 2026", metric="Earnings", value=100, unit="million USD")
    packet["sources"][0]["excerpt"] = fact["source_excerpt"] = "Quarter Q2 2026 earnings: 100 million USD."
    checks = {key: "supported" for key in FACT_FIELDS}
    checks.update(observed_at="not_applicable", reference_period="unsupported")
    checked = apply_fact_checks([fact], [{"fact_id": fact["id"], "checks": checks,
        "reason": "Value supported, but the source says Q2, not Q3."}], packet)[0]
    supported = fact_observation_is_supported(checked)
    record("R01", "Contradicted reference period", "Not source-supported",
           {"claim_status": checked["claim_status"], "supported": supported}, not supported)

    packet, fact = source_case()
    checks = {key: "supported" for key in FACT_FIELDS}
    reviewed = apply_fact_checks([fact], [{"fact_id": fact["id"], "checks": {**checks, "value": "unsupported"},
        "reason": "Wrong column", "correction": {"changes": {"value": 90.9}, "checks": checks,
        "reason": "The August column is 90.9."}}], packet)
    merged = merge_briefs([{"facts": reviewed, "source_packet": packet}, {"facts": [fact], "source_packet": packet}])
    old = next(row for row in merged["facts"] if row["id"] == fact["id"])
    record("R02", "Supersession survives raw-source merge", reviewed[0]["superseded_by"],
           old.get("superseded_by"), old.get("superseded_by") == reviewed[0]["superseded_by"])

    names = ["fertiliser", "gold miners", "silver miners", "oil producers", "uranium producers"]
    plays = [{"id": "p", "thesis": "Bullish on " + ", ".join(names) + "."}]
    components = [{"economic_key": name, "name": name, "source_text": name, "direction": "long"} for name in names]
    inventory = [{"play_id": "p", "components": [components[1]]}]
    complete = [{"play_id": "p", "components": components}]
    repair = AsyncMock(return_value={"play_components": complete})
    frozen = await establish_play_components(plays, inventory, repair, "mock/model", "2026-09-21")
    plan = complete_component_plan({"questions": []}, frozen, {})
    observed = {"inventory_status": frozen[0]["component_inventory_status"],
                "components": [row["name"] for row in frozen[0]["components"]], "repair_calls": repair.await_count,
                "coverage_rows": len(plan["component_coverage"])}
    record("R03", "Partial play decomposition", names, observed,
           set(observed["components"]) == set(names) or observed["inventory_status"] != "frozen")

    packet, fact = source_case()
    async def structure(lane, **kwargs):
        lane["evidence_brief"] = {"facts": [deepcopy(fact)], "source_packet": deepcopy(packet),
            "question_answers": [{"dimension": "price", "status": "answered", "answer": "Price established",
                                  "fact_ids": [fact["id"]]}]}
        return lane

    question = {"question": "Price and costs?", "required_dimensions": ["price", "costs"],
        "asset_classes": ["oil"], "inspect_source_ids": ["s"], "material_reason": "Evaluate margins",
        "reuse_assessment": "Inspect the report first"}
    runtime = PortfolioRuntime()
    token = CURRENT_RUNTIME.set(runtime)
    try:
        with patch.object(memo, "_structure_evidence_lane", structure), patch.object(memo.ParallelSourceProvider,
                "gather", AsyncMock(side_effect=RuntimeError("Supplementary provider unavailable"))):
            evidence, _, _ = await memo._run_question_research({"facts": [], "source_packet": packet},
                "deep", {"phase": "independent", "questions": [question]})
    finally:
        CURRENT_RUNTIME.reset(token)
    active = [row["id"] for row in evidence.get("facts", [])]
    record("R04", "Inspection survives supplementary failure", "Successful inspection remains active evidence",
        {"active_facts": active, "archived_inspections": len(runtime.partial.get("document_inspections", {}))}, bool(active))

    snapshot = {"portfolio": {"cash_pct": 50}, "asset_classes": [{"asset_class": "gold", "portfolio_pct": 50}]}
    proposal = {"asset_class_targets": [{"asset_class": "gold", "target_pct": 60, "funding_from": ["nonexistent"]},
        {"asset_class": "cash", "target_pct": 40}]}
    ledger = funding_ledger(snapshot, proposal)
    record("R05", "Invalid declared funding", "Funding explanation is explicitly unresolved",
        {key: ledger.get(key) for key in ("status", "issues", "funding_flow_status", "funding_flow_issues")},
        bool(ledger["issues"]) or ledger.get("funding_flow_status") == "unresolved")

    original = "Falling yields lower fixed-rate bond prices."
    document = decision_document({"current_sleeve_actions": [{"asset_class": "bonds", "action": "TRIM", "rationale": original}],
        "scenario_risks": [{"name": "Rates", "assumptions": [{"claim": original, "basis": "hypothetical", "fact_ids": []}]}]})
    patches = [{"path": path, "original": original,
        "replacement": "Falling yields raise existing fixed-rate bond prices, all else equal.",
        "reason": "Correct price-yield direction", "fact_ids": []} for path in (
            ["current_sleeve_actions", 0, "rationale"], ["scenario_risks", 0, "assumptions", 0, "claim"])]
    fixed = apply_claim_patches(document, {"patches": patches})
    record("R06", "Reviewed prose can be corrected", "Both financial prose patches apply",
        {"applied": len(fixed["claim_corrections"]),
         "rejected": [row["rejection_reason"] for row in fixed["unapplied_claim_corrections"]]}, len(fixed["claim_corrections"]) == 2)

    snapshot = {"portfolio": {"cash_pct": 100}, "asset_classes": [],
        "scenarios": [{"name": "Inflation", "shocks": {"inflation": 2}, "horizon_months": 12}]}
    proposal = {"asset_class_targets": [{"asset_class": "cash", "target_pct": 100}], "scenario_risks": [
        {"name": "Inflation", "mechanism": "Purchasing power risk", "exposures": [
            {"asset_class": "cash", "direction": "harm", "reason": "Purchasing power risk"}]}]}
    scenarios = implementation_comparison(snapshot, proposal, {})["destination"]["scenarios"]
    record("R07", "Incomplete numerical scenario retains qualitative analysis", "Qualitative impact retained",
        [{"status": row["status"], "directions": [exposure.get("direction") for exposure in row["rows"]]} for row in scenarios],
        any(exposure.get("direction") == "harm" for row in scenarios for exposure in row["rows"]))

    condition = {"metric": "yield", "benchmark": "Treasury", "unit": "%", "operator": "gt", "threshold": 4,
        "max_age_days": 7, "consecutive_count": 2, "max_gap_days": 2}
    observations = [{"metric": "yield", "benchmark": "Treasury", "unit": "%", "value": 5,
        "observed_at": date, "published_at": "2026-09-20T10:00:00Z", "source_url": "https://example.test"}
        for date in ("2026-09-20T09:00:00Z", "2026-09-20T09:00:00+00:00")]
    result = evaluate_conditions([condition], observations, "2026-09-21T02:00:00Z")[0]
    record("R08", "Monitoring counts distinct observations", "Unassessed: only one distinct timestamp",
        {"status": result["status"], "observation_count": len(result["observations"])}, result["status"] == "unassessed")

    attempts = []
    async def client(model, messages, **settings):
        await asyncio.sleep(.1)
        content = "not json" if not attempts else '{"answer":"ok"}'
        attempts.append(content)
        await settings["on_progress"]({"activity": "receiving_text", "content_delta": content})
        return {"content": content, "finish_reason": "stop", "usage": {"completion_tokens": 20}}
    client.supports_progress = True
    runtime = PortfolioRuntime()
    await runtime.query(client, "mock/model", [{"role": "user", "content": json.dumps({"task": "timing audit",
        "required_schema": {"answer": "string"}})}],
        parser=lambda text: json.loads(text) if text.startswith("{") else None, validator=lambda value, prompt: [])
    timings = [row["timing"]["time_to_first_token_seconds"] for row in runtime.receipts]
    record("R09", "Retry first-token timing", "Each attempt waits at least 0.1 seconds for its first token",
           timings, len(timings) == 2 and all(value >= .09 for value in timings))
    return results


if __name__ == "__main__":
    results = asyncio.run(audit())
    print(json.dumps({"checks": results, "unresolved": sum(not row["passed"] for row in results)}, indent=2))
    raise SystemExit(int(any(not row["passed"] for row in results)))
