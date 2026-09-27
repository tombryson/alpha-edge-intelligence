"""Portfolio decision arithmetic. Unknown exposures are never inferred from labels."""

from __future__ import annotations

import math
import re
from copy import deepcopy

from .portfolio_evidence import timestamp, fact_is_supported, fact_observation_is_supported
from .portfolio_runtime import business_data, digest, utc_now, receipt_error


def number(value):
    if isinstance(value, bool) or value in (None, ""):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def asset_key(value):
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


MANDATE_FIELDS = ("base_currency", "benchmark", "horizon_months", "max_drawdown_pct", "liquidity_min_pct", "tax_cost_policy", "currency_hedge_policy")
TIME_HORIZON_CEILINGS = {"1-2 years": 24, "3-5 years": 60, "5+ years": None}


def supplied(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in {"", "unknown", "unassessed", "not assessed", "n/a", "tbd", "none", "null"}
    return value is not None and not isinstance(value, bool)


def missing_mandate_fields(mandate: dict) -> list[str]:
    return [key for key in MANDATE_FIELDS if not supplied(mandate.get(key)) and not (
        key == "horizon_months" and isinstance(mandate.get("time_horizon"), str)
        and mandate["time_horizon"] in TIME_HORIZON_CEILINGS)]


def mandate_horizon_ceiling(mandate: dict):
    band = mandate.get("time_horizon")
    if isinstance(band, str) and band in TIME_HORIZON_CEILINGS:
        return TIME_HORIZON_CEILINGS[band]
    return number(mandate.get("horizon_months"))


def mandate_issues(mandate: dict) -> list[str]:
    issues = [f"Missing {key.replace('_', ' ')}" for key in missing_mandate_fields(mandate)]
    for key, choices in (("risk_tolerance", ("low", "medium", "high")), ("time_horizon", TIME_HORIZON_CEILINGS)):
        value = mandate.get(key)
        if supplied(value) and (not isinstance(value, str) or value not in choices):
            issues.append(f"Invalid {key.replace('_', ' ')}")
    currency = mandate.get("base_currency")
    if supplied(currency) and (not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency)):
        issues.append("Base currency must be a three-letter currency code")
    for key, upper in (("horizon_months", None), ("max_drawdown_pct", 100), ("liquidity_min_pct", 100)):
        if not supplied(mandate.get(key)):
            continue
        value = number(mandate[key])
        if value is None or value < 0 or (key == "horizon_months" and value == 0) or (upper is not None and value > upper):
            issues.append(f"Invalid {key.replace('_', ' ')}")
    return issues


def funding_ledger(snapshot: dict, proposal: dict) -> dict:
    from .portfolio_exposures import reference_links
    current = {asset_key(r.get("asset_class")): r for r in snapshot.get("asset_classes", [])}
    duplicate_current = len(current) != len(snapshot.get("asset_classes", []))
    current.setdefault("CASH", {"asset_class": "cash", "display_name": "Cash", "portfolio_pct": snapshot.get("portfolio", {}).get("cash_pct")})
    target_rows = proposal.get("asset_class_targets") or []
    actions = {asset_key(r.get("asset_class")): r for r in proposal.get("current_sleeve_actions", [])}
    ledger, seen, issues, unresolved_actions = [], set(), [], []
    links, mapping_issues = reference_links(proposal, "holdings", list(current.values()))
    issues.extend(mapping_issues)
    declarations = {asset_key(row.get("asset_class")): row.get("baseline_links", [])
                    for row in proposal.get("reconciliation", []) if isinstance(row, dict)}
    unresolved_sources = set()
    attributed = {}
    if duplicate_current:
        issues.append("Duplicate current asset classes")
    for row in current.values():
        weight = number(row.get("portfolio_pct"))
        if weight is None or not 0 <= weight <= 100:
            issues.append(f"Missing or invalid current weight for {row.get('asset_class')}")
    for target in target_rows:
        key = asset_key(target.get("asset_class"))
        if not key or key in seen:
            issues.append("Duplicate or unnamed allocation row")
            continue
        seen.add(key)
        source_links = links.get(key, [])
        declared = target.get("baseline_links") or declarations.get(key) or []
        requested_sources = {asset_key(link.get("asset_class")) for link in declared if isinstance(link, dict)
                             and link.get("view") == "holdings" and link.get("relationship") in {"equivalent", "partial_overlap"}
                             and not (target.get("position_identity") == "new" and link.get("relationship") == "partial_overlap" and link.get("capital_component") is not True)}
        rejected_sources = requested_sources - {link["source_key"] for link in source_links}
        unresolved_sources.update(rejected_sources)
        source_weights = [number(current[link["source_key"]].get("portfolio_pct")) for link in source_links]
        before = (sum(weight * link["share_pct"] / 100 for weight, link in zip(source_weights, source_links))
                  if all(weight is not None for weight in source_weights) else None)
        if any(actions.get(source, {}).get("action") != "EXIT" for source in rejected_sources):
            before = None
        for link in source_links:
            attributed[link["source_key"]] = attributed.get(link["source_key"], 0) + link["share_pct"]
        after = number(target.get("target_pct"))
        lo, hi = number(target.get("min_pct")), number(target.get("max_pct"))
        has_range = "min_pct" in target or "max_pct" in target
        if after is None or not 0 <= after <= 100 or has_range and (lo is None or hi is None or not 0 <= lo <= after <= hi <= 100):
            issues.append(f"Invalid allocation range for {target.get('asset_class')}")
        ledger.append({**business_data(target), "action": target.get("action") or actions.get(key, {}).get("action"),
                       "action_basis": target.get("action_basis") or actions.get(key, {}).get("action_basis") or {},
                       "current_pct": before, "target_pct": after,
                       "trade_pct": round(after - before, 4) if after is not None and before is not None else None,
                       "status": "specified" if after is not None else "unresolved"})
    for key, row in current.items():
        remaining = max(0, 1 - attributed.get(key, 0) / 100)
        if remaining == 0 or (number(row.get("portfolio_pct")) == 0 and key != "CASH"):
            continue
        action = actions.get(key, {})
        original_weight = number(row.get("portfolio_pct"))
        before = original_weight * remaining if original_weight is not None else None
        if key in unresolved_sources and action.get("action") != "EXIT":
            # A rejected capital mapping is unresolved, not a second allocation.
            unresolved_actions.append({**business_data(action), "asset_class": row.get("asset_class"),
                "current_pct": before, "reason": "The declared target relationship needs reconciliation; its action weight is not additional capital."})
            continue
        stated = number(action.get("target_pct"))
        after = 0.0 if action.get("action") == "EXIT" else (before if action.get("action") == "HOLD" else stated)
        if after is None:
            issues.append(f"No final weight specified for {row.get('display_name') or row.get('asset_class')}")
        elif not 0 <= after <= 100:
            issues.append(f"Invalid final weight for {row.get('asset_class')}")
        ledger.append({"asset_class": row.get("asset_class"), "display_name": row.get("display_name"), "action": action.get("action"),
                       "action_basis": action.get("action_basis") or {},
                       "current_pct": before, "target_pct": after, "min_pct": after, "max_pct": after,
                       "trade_pct": round(after - before, 4) if after is not None and before is not None else None,
                       "status": "specified" if after is not None else "unresolved", "rationale": action.get("rationale", "")})
    known_total = sum(row["target_pct"] for row in ledger if row["target_pct"] is not None)
    weights = [number(row.get("portfolio_pct")) for row in current.values()]
    current_total = sum(weights) if all(weight is not None for weight in weights) else None
    if current_total is not None and abs(current_total - 100) > 0.1:
        issues.append(f"Current weights total {current_total:.2f}%; reconcile the snapshot")
    if abs(known_total - 100) > 0.05:
        issues.append(f"Specified final weights total {known_total:.2f}%")
    if not target_rows:
        issues.append("No final allocation selected")
    mandate = snapshot.get("mandate") or {}
    liquidity = number(mandate.get("liquidity_min_pct"))
    cash_keys = {"CASH"} | {key for key, values in links.items() if any(
        link["source_key"] == "CASH" and link.get("relationship") == "equivalent" for link in values)}
    cash_rows = [row for row in ledger if asset_key(row["asset_class"]) in cash_keys
                 or row.get("liquidity_class") in {"cash", "cash_equivalent"}]
    cash = sum(row["target_pct"] for row in cash_rows) if cash_rows and all(row["target_pct"] is not None for row in cash_rows) else None
    if liquidity is not None and cash is not None and cash < liquidity:
        issues.append("Cash target is below the specified liquidity minimum")
    for row in ledger:
        delta = row["trade_pct"]
        row["reference_trade_action"] = "REVIEW" if delta is None else "ADD" if delta > 0.05 else "TRIM" if delta < -0.05 else "HOLD"
        low, high, before = number(row.get("min_pct")), number(row.get("max_pct")), row["current_pct"]
        recorded = str(row.get("positioning_stance") or row.get("action") or "").upper()
        row["positioning_stance"] = recorded if recorded in {"ADD", "TRIM", "HOLD", "EXIT", "REVIEW", "WATCH"} else (
            row["reference_trade_action"] if before is not None and low is None and high is None else
            "REVIEW" if before is None or low is None or high is None else
            "HOLD" if low <= before <= high else "ADD" if before < low else "TRIM")
        row["action"] = row["positioning_stance"]
        row["trade_value"] = round(delta * number(snapshot.get("portfolio", {}).get("total_value")) / 100, 2) if delta is not None and number(snapshot.get("portfolio", {}).get("total_value")) is not None else None
    if any(row["current_pct"] is None for row in ledger):
        issues.append("Current capital attribution remains unresolved")
    reductions = {asset_key(row["asset_class"]): row for row in ledger if row.get("trade_pct") is not None and row["trade_pct"] < -.05}
    uses = [row for row in ledger if row.get("trade_pct") is not None and row["trade_pct"] > .05]
    flow_issues = [{"asset_class": row["asset_class"], "source": source, "reason": "Declared funding source has no recorded reduction"}
                   for row in uses for source in row.get("funding_from", []) if asset_key(source) not in reductions]
    return {"status": "balanced" if not issues else "unresolved", "trade_status": "proposed_not_executed", "rows": ledger,
            "funding_sources": [{"asset_class": row["asset_class"], "available_pct": -row["trade_pct"]} for row in reductions.values()],
            "funding_uses": [{"asset_class": row["asset_class"], "required_pct": row["trade_pct"], "declared_sources": row.get("funding_from", [])} for row in uses],
            "funding_flow_issues": flow_issues,
            "funding_flow_status": "unresolved" if flow_issues else "unassessed" if any(not row.get("funding_from") for row in uses) else "consistent",
            "unresolved_current_actions": unresolved_actions,
            "cash_target_pct": cash,
            "current_total_pct": round(current_total, 4) if current_total is not None else None, "specified_target_total_pct": round(known_total, 4),
            "unallocated_pct": round(100 - known_total, 4), "issues": issues,
            "one_way_turnover_pct": round(sum(abs(r["trade_pct"] or 0) for r in ledger) / 2, 4) if not issues else None}


def allocation_disagreements(lanes: list[dict]) -> list[dict]:
    assets = {}
    for index, lane in enumerate(lanes):
        proposal = lane.get("macro_positioning", lane)
        for row in proposal.get("asset_class_targets") or []:
            assets.setdefault(row["asset_class"], {})[str(lane.get("lane") or lane.get("council_lane") or index)] = row.get("target_pct")
    return [{"asset_class": key, "proposals": values, "omitted_in_other_lanes": len(values) < len(lanes)}
            for key, values in assets.items() if len(set(values.values())) > 1 or len(values) < len(lanes)]


def build_decision(snapshot: dict, proposal: dict, evidence: dict) -> dict:
    ledger = funding_ledger(snapshot, proposal)
    mandate = business_data(snapshot.get("mandate") or {})
    facts = {r["id"]: r for r in evidence.get("facts", []) if isinstance(r, dict) and r.get("id")}
    missing = missing_mandate_fields(mandate)
    constraints = mandate_issues(mandate)
    assumptions = []
    if "research_questions" in evidence:
        from .portfolio_research import current_research_questions
        market_questions = [row for row in current_research_questions(evidence) if row["status"] != "answered"]
    else:
        market_questions = evidence.get("unresolved_market_questions", [])
    for row in ledger["rows"]:
        refs = row.get("fact_ids") or []
        matched = [ref for ref in refs if isinstance(ref, str) and fact_observation_is_supported(facts.get(ref, {}))]
        implementation = row.get("implementation") or {}
        unverified = []
        decision_pending = row.get("decision_review_status") == "unresolved"
        if (row.get("action_basis") or {}).get("category") == "research_gap" and abs(row.get("trade_pct") or 0) > .05:
            decision_pending = True
            row["decision_review_status"] = "unresolved"
            unverified.append("The proposed change needs an investment or risk justification beyond missing research")
        if decision_pending:
            unverified.append("This decision remains under review after a material correction")
        unresolved_market = [item["question"] for item in market_questions
                             if asset_key(row["asset_class"]) in {asset_key(asset) for asset in item.get("asset_classes", [])}]
        unverified.extend(f"Market question remains unanswered: {question}" for question in unresolved_market)
        if not matched:
            unverified.append("The allocation's cited facts have not been checked against their sources")
        elif len(matched) != len(refs):
            unverified.append("Some cited facts have not been matched to their sources")
        metadata_pending = [ref for ref in matched if not fact_is_supported(facts[ref])]
        if metadata_pending:
            unverified.append("Some supporting observations have unverified publication dates or release versions")
            row["evidence_qualifications"] = [{"fact_id": ref, "dimensions": facts[ref].get("review_dimensions")} for ref in metadata_pending]
        if not supplied(implementation.get("instrument_type")) or not supplied(implementation.get("currency")):
            unverified.append("Instrument type or currency not specified")
        if not isinstance(implementation.get("risk_attributes"), dict) or not any(value not in (None, "", "unknown") for value in implementation["risk_attributes"].values()):
            unverified.append("Risk attributes not specified")
        else:
            for key in ("duration_years", "credit_quality", "currency_hedging", "operating_stage"):
                if not supplied(implementation["risk_attributes"].get(key)):
                    unverified.append(f"{key.replace('_', ' ').capitalize()} not established")
        pricing = row.get("market_pricing") or {}
        if not supplied(pricing.get("observed_expectation")) or not supplied(pricing.get("benchmark")) or not any(
            isinstance(ref, str) and fact_observation_is_supported(facts.get(ref, {})) and facts[ref].get("kind") in {"market_price", "implied_expectation"} and asset_key(facts[ref].get("benchmark")) == asset_key(pricing.get("benchmark"))
            for ref in pricing.get("fact_ids") or []):
            unverified.append("Market-implied expectations have not been substantiated")
        investment_case = row.get("investment_case") or {}
        for key in ("why_better_than_hold", "why_better_than_cash", "downside", "cost_assumptions", "horizon_months"):
            if not supplied(investment_case.get(key)):
                unverified.append(f"Investment case missing: {key.replace('_', ' ')}")
        horizon = number(investment_case.get("horizon_months"))
        if horizon is None or horizon <= 0:
            unverified.append("Investment holding period has not been established")
        elif mandate_horizon_ceiling(mandate) is not None and horizon > mandate_horizon_ceiling(mandate):
            unverified.append("Investment holding period exceeds the portfolio mandate")
        if not any(isinstance(item, dict) and supplied(item.get("name")) and supplied(item.get("why_preferred")) for item in row.get("alternatives") or []):
            unverified.append("No comparison with holding or cash")
        if not any(isinstance(item, str) and supplied(item) for item in row.get("contrary_evidence") or []):
            unverified.append("Contrary evidence not documented")
        if evidence.get("evidence_status") != "complete":
            unverified.append("Evidence reconciliation is incomplete")
        requested = str(row.get("thesis_conviction") or row.get("conviction") or "UNASSESSED").upper()
        row["thesis_conviction"] = requested if requested in {"STRONG", "MEDIUM", "WEAK", "UNASSESSED"} else "UNASSESSED"
        row["conviction"] = row["thesis_conviction"]
        row["sizing_confidence"] = "UNASSESSED"
        row["research_status"] = "supported" if matched and not unresolved_market and not decision_pending else "needs_verification"
        if unresolved_market:
            row["unanswered_market_questions"] = unresolved_market
        else:
            row.pop("unanswered_market_questions", None)
        row["open_questions"] = unverified
        assumptions.extend({"asset_class": row["asset_class"], "question": item,
                            "trade_size_pct": abs(row["trade_pct"] or 0)} for item in unverified)
    assumptions.sort(key=lambda row: row["trade_size_pct"], reverse=True)
    decision = {"schema_version": 3, "funding": ledger, "mandate": mandate, "missing_mandate": missing,
            "mandate_issues": constraints, "decision_at": snapshot.get("decision_at", snapshot.get("as_of")),
            "research_priorities": assumptions, "market_view": business_data(evidence.get("quadrant_assessment") or {}),
            "status": "ready_for_review" if not constraints and not assumptions and ledger["status"] == "balanced" else "needs_review",
            "decision_hash": digest({"snapshot": snapshot, "proposal": business_data(proposal), "facts": list(facts.values())})}
    decision["allocation_hash"] = digest({"rows": sorted([
        {"asset_class": asset_key(row["asset_class"]), "weight": row["target_pct"], "implementation": row.get("implementation")}
        for row in ledger["rows"]], key=lambda row: row["asset_class"]),
        "base_currency": mandate.get("base_currency"), "horizon_months": number(mandate.get("horizon_months")),
        **{key: mandate[key] for key in ("risk_tolerance", "time_horizon") if supplied(mandate.get(key))}})
    checks = []
    review = proposal.get("mandate_review") or {}
    for key in ("tax_cost_policy", "currency_hedge_policy"):
        item = review.get(key) or {}
        assessed = (isinstance(item, dict) and item.get("policy") == mandate.get(key) and supplied(item.get("reason"))
                    and item.get("status") in {"compliant", "breach"})
        checks.append({"constraint": key, "status": item["status"] if assessed else "unassessed",
                       "reason": item.get("reason") if assessed else "The proposal has not been assessed against this policy"})
    scenarios = scenario_comparison(decision, snapshot.get("scenarios") or [], snapshot.get("risk_exposures") or {})
    losses = [-item["proposed_return_pct"] for item in scenarios if item["status"] == "calculated"]
    tolerance = number(mandate.get("max_drawdown_pct"))
    risk = snapshot.get("risk_assessment") or {}
    estimate = number(risk.get("estimated_max_drawdown_pct"))
    risk_date, review_date = timestamp(risk.get("as_of")), timestamp(snapshot.get("review_at") or utc_now())
    risk_supported = (risk.get("allocation_hash") == decision["allocation_hash"] and estimate is not None and 0 <= estimate <= 100
                      and risk_date and review_date and risk_date <= review_date and supplied(risk.get("method")) and supplied(risk.get("source_url")))
    # Scenario terminal losses can establish a breach, but cannot certify a drawdown limit.
    breached = tolerance is not None and (any(loss > tolerance for loss in losses) or (risk_supported and estimate > tolerance))
    checks.append({"constraint": "max_drawdown_pct", "status": "breach" if breached else "compliant" if risk_supported and tolerance is not None else "unassessed",
                   "reason": "The supplied risk estimate or scenario exceeds the loss tolerance" if breached else
                   f"Supplied drawdown estimate {estimate:g}%, conditional on {risk['method']}; not a loss guarantee" if risk_supported else
                   "A dated risk estimate for this allocation is still required; terminal scenario returns do not establish maximum drawdown"})
    cash = ledger.get("cash_target_pct")
    minimum = number(mandate.get("liquidity_min_pct"))
    checks.append({"constraint": "liquidity_min_pct", "status": "unassessed" if cash is None or minimum is None else "breach" if cash < minimum else "compliant",
                   "reason": "Proposed cash compared with the specified minimum"})
    decision["mandate_checks"] = checks
    if any(check["status"] != "compliant" for check in checks):
        decision["status"] = "needs_review"
    elif decision["status"] == "ready_for_review":
        for row in ledger["rows"]:
            row["sizing_confidence"] = "CONDITIONAL"
    return decision


def decision_for_artifact(artifact: dict, *, mandate: dict | None = None, exposures=None, scenarios=None, risk_assessment=None, review_at=None) -> dict:
    snapshot = dict(artifact.get("portfolio_snapshot") or {})
    snapshot["decision_at"] = snapshot.get("decision_at") or artifact.get("updated_at") or (artifact.get("structured_data") or {}).get("analysis_date")
    if mandate is not None:
        snapshot["mandate"] = mandate
    if exposures is not None:
        snapshot["risk_exposures"] = exposures
    if scenarios is not None:
        snapshot["scenarios"] = scenarios
    if risk_assessment is not None:
        snapshot["risk_assessment"] = risk_assessment
    snapshot["review_at"] = review_at or utc_now()
    decision = build_decision(snapshot, artifact.get("macro_positioning") or artifact.get("structured_data") or {}, artifact.get("evidence_brief") or {})
    if artifact.get("pipeline_error") or artifact.get("pipeline_status") in {"failed", "running"} or (artifact.get("analysis_health") or {}).get("status") == "incomplete":
        decision["status"] = "needs_review"
        for row in decision["funding"]["rows"]:
            row["sizing_confidence"] = "UNASSESSED"
    return decision


def recorded_display_rows(artifact: dict, field="asset_class_targets") -> list[dict]:
    """Expose recorded model conviction even when an older assembler hid it."""
    proposal = artifact.get("macro_positioning") or artifact.get("structured_data") or {}
    proposals = {asset_key(row.get("asset_class")): row for row in proposal.get("asset_class_targets", [])}
    if field == "current_sleeve_decisions" and artifact.get("workflow_version", 0) >= 3:
        # The sealed current-aware assessment is a baseline, not the final decision.
        actions = {asset_key(row.get("asset_class")): row for row in proposal.get("current_sleeve_actions", [])}
        snapshot = artifact.get("portfolio_snapshot") or {}
        holdings = list(snapshot.get("asset_classes") or [])
        cash = (snapshot.get("portfolio") or {}).get("cash_pct")
        if cash is not None and not any(asset_key(row.get("asset_class")) == "CASH" for row in holdings):
            holdings.append({"asset_class": "cash", "display_name": "Cash", "portfolio_pct": cash})
        rows = []
        for holding in holdings:
            key = asset_key(holding.get("asset_class"))
            settled = actions.get(key) or proposals.get(key) or {}
            rows.append({"asset_class": holding.get("asset_class"),
                "display_name": holding.get("display_name") or settled.get("display_name"),
                "current_pct": holding.get("portfolio_pct"), "action": settled.get("action") or "REVIEW",
                **{name: deepcopy(settled[name]) for name in ("rationale", "thesis_conviction", "related_or_substitute_exposure") if name in settled}})
    else:
        rows = deepcopy((artifact.get("structured_data") or {}).get(field) or [])
    for row in rows:
        source = proposals.get(asset_key(row.get("asset_class")), {})
        conviction = source.get("thesis_conviction") or row.get("thesis_conviction") or row.get("conviction")
        if conviction:
            row["model_thesis_conviction"] = conviction
    return rows


def analysis_health(artifact: dict) -> dict:
    issues = []
    warnings = []
    if artifact.get("pipeline_error") or artifact.get("pipeline_status") in {"running", "failed"}:
        issues.append({"stage": "pipeline", "detail": artifact.get("pipeline_error") or "Processing has not finished"})
    evidence_runs = artifact.get("evidence_runs") or []
    for lane in evidence_runs:
        if lane.get("error") or (lane.get("evidence_brief") or {}).get("stage_error"):
            (warnings if lane.get("supplementary") else issues).append({"stage": lane.get("label") or "research", "detail": lane.get("error") or lane["evidence_brief"]["stage_error"]})
    labels = {lane.get("label") for lane in evidence_runs}
    for expected in artifact.get("expected_evidence_lanes") or []:
        if expected not in labels:
            issues.append({"stage": "research", "detail": f"Required evidence lane missing: {expected}"})
    brief = artifact.get("evidence_brief") or {}
    structured = artifact.get("structured_data") or {}
    receipts = artifact.get("stage_receipts") or []
    by_input = {}
    for row in receipts:
        by_input[row.get("input_hash") or row.get("stage")] = row
    for row in by_input.values():
        if row.get("status") != "complete":
            (warnings if row.get("optional") else issues).append({"stage": row.get("stage"), "detail": receipt_error(row),
                           "failure_type": row.get("failure_type"), "model": row.get("model")})
    for detail in brief.get("research_limitations") or []:
        warnings.append({"stage": "research", "severity": "warning", "detail": detail})
    for row in by_input.values():
        if row.get("warnings"):
            details = row["warnings"]
            warnings.append({"stage": row.get("stage"), "severity": "warning", "model": row.get("model"),
                             "detail": details[0]["detail"] if len(details) == 1 else f"{len(details)} review or detail fields remain unresolved; usable output retained.",
                             "fields": details})
    if brief.get("evidence_status") == "incomplete" or (brief.get("evidence_ensemble") or {}).get("mode") in {"fallback_first_valid", "unreconciled"}:
        issues.append({"stage": "evidence", "detail": "Evidence reconciliation incomplete"})
    if (brief.get("asset_class_coverage_quality") or {}).get("status") in {"failed_all_none", "unassessed"}:
        warnings.append({"stage": "coverage", "severity": "warning",
                         "detail": "Asset-class coverage has not been verified; the completed analysis is retained for review."})
    consensus = (artifact.get("portfolio_memo_ensemble") or {}).get("consensus") or structured.get("portfolio_memo_ensemble_consensus") or {}
    if str(consensus.get("mode", "")).startswith(("fallback", "unreconciled")):
        issues.append({"stage": "synthesis", "detail": "No completed comparison selected the final allocation"})
    for lane in (artifact.get("portfolio_memo_ensemble") or {}).get("lanes") or []:
        if lane.get("error"):
            issues.append({"stage": lane.get("lane"), "detail": lane["error"]})
        for role in lane.get("allocator_council_runs") or []:
            if role.get("error") or not role.get("asset_class_targets"):
                issues.append({"stage": role.get("council_lane") or role.get("lane_strategy") or "allocator", "detail": role.get("error") or "Allocator did not produce a proposal"})
    decision = decision_for_artifact(artifact)
    for issue in decision["funding"]["issues"]:
        issues.append({"stage": "allocation", "detail": issue})
    if not receipts:
        warnings.append({"stage": "provenance", "detail": "Per-stage records were not saved with this historical memo"})
    if not artifact.get("workflow_version") and not receipts and not artifact.get("pipeline_status"):
        return {"status": "historical", "label": "Historical memo", "issues": [],
                "warnings": warnings + issues, "decision_status": decision["status"], "missing_mandate": decision["missing_mandate"],
                "decision_label": "Current implementation review available"}
    if artifact.get("workflow_version", 0) >= 3:
        # A partial provider or implementation failure qualifies the memo, not every investment judgment.
        critical = [item for item in issues if item["stage"] == "pipeline"]
        warnings.extend(item for item in issues if item not in critical)
        issues = critical
        if not (artifact.get("independent_ideal") or {}).get("asset_class_targets"):
            issues.append({"stage": "independent ideal", "detail": "The independent portfolio view is not yet complete"})
        if not (artifact.get("macro_positioning") or {}).get("asset_class_targets"):
            issues.append({"stage": "final recommendation", "detail": "No final portfolio has been selected; retained analysis remains available"})
        current = artifact.get("current_portfolio_assessment") or {}
        if not current.get("executive_summary") and not current.get("current_assessment"):
            issues.append({"stage": "current portfolio", "detail": "The current portfolio assessment is incomplete; the independent view is retained"})
        reconsideration = (artifact.get("macro_positioning") or {}).get("decision_reconsideration") or {}
        if reconsideration.get("status") == "unresolved":
            warnings.append({"stage": "decision review", "detail": "The memo is retained; affected investment decisions still require review after a material correction."})
    return {"status": "incomplete" if issues else "complete",
            "label": "Credit check required; completed work saved" if artifact.get("pipeline_status") == "awaiting_credit" else "Analysis incomplete" if issues else "Analysis complete with limitations" if warnings else "Analysis complete",
            "issues": issues + warnings, "warnings": warnings, "decision_status": decision["status"], "missing_mandate": decision["missing_mandate"],
            "decision_label": "Allocation requires review" if decision["status"] == "needs_review" else "Allocation ready for review"}


def scenario_comparison(decision: dict, scenarios: list[dict], exposures: dict) -> list[dict]:
    """Linear factor attribution; returns stay unknown when a required input is absent."""
    results = []
    exposures = {asset_key(key): value for key, value in exposures.items()}
    for scenario in scenarios:
        shocks = scenario.get("shocks") or {}
        horizon = number(scenario.get("horizon_months"))
        rows = []
        benchmark_key = asset_key(decision.get("mandate", {}).get("benchmark"))
        allocations = list(decision["funding"]["rows"])
        if benchmark_key and not any(asset_key(row["asset_class"]) == benchmark_key for row in allocations):
            allocations.append({"asset_class": decision["mandate"]["benchmark"], "current_pct": 0, "target_pct": 0, "comparison_only": True})
        for row in allocations:
            if row.get("current_pct") == 0 and row.get("target_pct") == 0 and asset_key(row["asset_class"]) != benchmark_key:
                continue
            exposure = exposures.get(asset_key(row["asset_class"])) or {}
            sensitivities = exposure.get("sensitivities") or {}
            errors = []
            if not shocks:
                errors.append("No scenario shocks supplied")
            effects = []
            for factor, shock in shocks.items():
                sensitivity = number(sensitivities.get(factor))
                change = number(shock)
                if sensitivity is None or change is None:
                    errors.append(f"Missing {factor} sensitivity or shock")
                else:
                    effects.append(sensitivity * change)
            carry = number(exposure.get("annual_carry_pct"))
            if carry is None or horizon is None or horizon <= 0:
                errors.append("Missing carry or holding period")
            cost = number(exposure.get("transaction_cost_bps"))
            if cost is None or cost < 0:
                errors.append("Trading costs not specified")
            if not exposure.get("basis") or not exposure.get("source"):
                errors.append("Sensitivity source/basis not supplied")
            if not exposure.get("currency") or not decision["mandate"].get("base_currency"):
                errors.append("Currency not specified")
            elif exposure.get("currency") != decision["mandate"].get("base_currency") and "fx_return_pct" not in shocks:
                errors.append("Base-currency return requires FX or hedged exposure")
            estimate = None if errors else sum(effects) + carry * horizon / 12
            old, new = number(row["current_pct"]), number(row["target_pct"])
            rows.append({"asset_class": row["asset_class"], "return_pct": estimate,
                         "comparison_only": row.get("comparison_only", False),
                         "current_contribution_pp": estimate * old / 100 if estimate is not None and old is not None else None,
                         "proposed_contribution_pp": estimate * new / 100 - abs(new - old) * cost / 10000 if estimate is not None and old is not None and new is not None else None,
                         "assumption_basis": exposure.get("basis"), "missing_inputs": errors})
        portfolio_rows = [row for row in rows if not row["comparison_only"]]
        complete = bool(portfolio_rows) and decision["funding"]["status"] == "balanced" and all(r["proposed_contribution_pp"] is not None for r in portfolio_rows)
        old_total = sum(r["current_contribution_pp"] for r in portfolio_rows) if complete else None
        new_total = sum(r["proposed_contribution_pp"] for r in portfolio_rows) if complete else None
        benchmark_row = next((row for row in rows if asset_key(row["asset_class"]) == benchmark_key), None)
        benchmark_return = benchmark_row.get("return_pct") if benchmark_row else None
        results.append({"name": scenario.get("name"), "status": "calculated" if complete else "incomplete", "rows": rows,
                        "benchmark": {"name": decision.get("mandate", {}).get("benchmark"), "return_pct": benchmark_return,
                                      "status": "calculated" if benchmark_return is not None else "unassessed"},
                        "hold_return_pct": old_total, "proposed_return_pct": new_total,
                        "improvement_pp": new_total - old_total if complete else None,
                        "method": "Linear factor sensitivity plus prorated carry, less one-time trading costs; scenario, not forecast"})
    return results


def evaluate_conditions(conditions: list[dict], observations: list[dict], as_of: str) -> list[dict]:
    from .portfolio_evidence import availability
    results = []
    now = timestamp(as_of)
    comparisons = {"gt": lambda a, b: a > b, "gte": lambda a, b: a >= b, "lt": lambda a, b: a < b, "lte": lambda a, b: a <= b}
    for condition in conditions:
        if not isinstance(condition, dict):
            results.append({"status": "unassessed", "reason": "Untyped review note"})
            continue
        binding = condition.get("series_binding") or condition
        identity = ("metric", "benchmark", "unit")
        series = {key: binding.get(key) for key in (*identity, "quote_convention")}
        identifier = condition.get("id") or "condition_" + digest({"series": series, **{key: condition.get(key) for key in
            ("threshold", "operator", "consecutive_count", "max_gap_days", "max_age_days")}})[:20]
        matching = [o for o in observations if all(supplied(binding.get(k)) and o.get(k) == binding.get(k) for k in identity)
            and (o.get("quote_convention") or (o.get("measurement") or {}).get("quote_convention")) == binding.get("quote_convention")
            and not o.get("superseded_by") and o.get("claim_status") != "unsupported"]
        matching = [o for o in matching if timestamp(o.get("published_at")) and now and timestamp(o["published_at"]) <= now and timestamp(o.get("observed_at")) and timestamp(o["observed_at"]) <= now]
        matching = [o for o in matching if all(availability(o.get(field), as_of) != "timezone_unknown"
                                              for field in ("observed_at", "published_at"))]
        observation = max(matching, key=lambda o: (timestamp(o["observed_at"]), timestamp(o["published_at"]))) if matching else None
        ambiguous = observation and len({number(o.get("value")) for o in matching if timestamp(o["observed_at"]) == timestamp(observation["observed_at"]) and timestamp(o["published_at"]) == timestamp(observation["published_at"])}) > 1
        value, threshold = number((observation or {}).get("value")), number(condition.get("threshold"))
        op = comparisons.get(condition.get("operator"))
        max_age = number(condition.get("max_age_days"))
        reason = ("No matching dated series with the specified unit and sign convention" if not observation else
                  "Conflicting observations at the same timestamp" if ambiguous else
                  "A numeric threshold and supported operator are required" if value is None or threshold is None or not op else
                  "Freshness policy is undefined" if max_age is None or max_age < 0 else
                  "Latest observation is stale" if (now - timestamp(observation["observed_at"])).total_seconds() > max_age * 86400 else
                  "Observation source is unavailable" if not observation.get("source_url") else None)
        count = condition.get("consecutive_count", 1)
        sequence = []
        if not reason and (type(count) is not int or count < 1):
            reason = "Persistence count must be a positive integer"
        if not reason:
            dated = {}
            for row in matching:
                period = row.get("reference_period") or (row.get("measurement") or {}).get("reference_period")
                date = ("period", str(period)) if period else ("instant", timestamp(row["observed_at"]))
                dated.setdefault(date, []).append(row)
            latest = []
            for versions in dated.values():
                published = max(timestamp(row["published_at"]) for row in versions)
                current = [row for row in versions if timestamp(row["published_at"]) == published]
                latest.append((current[0], len({number(row.get("value")) for row in current}) > 1))
            selected = sorted(latest, key=lambda item: timestamp(item[0]["observed_at"]), reverse=True)[:count]
            sequence = [row for row, _ in selected]
            gap = number(condition.get("max_gap_days"))
            if any(conflict for _, conflict in selected):
                reason = "Conflicting observations in the required sequence"
            elif count > 1 and (gap is None or gap <= 0):
                reason = "Persistence requires a maximum gap between observations"
            elif len(sequence) < count:
                reason = "Insufficient observations for the required persistence"
            elif count > 1 and any((timestamp(a["observed_at"]) - timestamp(b["observed_at"])).total_seconds() > gap * 86400
                                   for a, b in zip(sequence, sequence[1:])):
                reason = "Observations do not establish a continuous sequence"
            elif any(number(row.get("value")) is None or not row.get("source_url") for row in sequence):
                reason = "Sequence contains an unavailable value or source"
        triggered = not reason and all(op(number(row["value"]), threshold) for row in sequence)
        results.append({"id": identifier, "status": "unassessed" if reason else "triggered" if triggered else "not_triggered",
                        "reason": reason, "series_binding": series, "observations": sequence,
                        "observation": observation, "what_changes": condition.get("what_changes"), "owner": condition.get("owner"), "next_review": condition.get("next_review")})
    return results


def return_record_issues(decision: dict, result: dict, as_of: str) -> list[str]:
    start, end = timestamp(result.get("from")), timestamp(result.get("to"))
    origin, now = timestamp(decision.get("decision_at")), timestamp(as_of)
    issues = []
    if not origin or not now or not start or not end or start < origin or end > now or end <= start:
        issues.append("Return period must start at or after the decision and end by the review date")
    published = timestamp(result.get("published_at")) if result.get("published_at") else None
    if result.get("published_at") and (not published or not now or published > now):
        issues.append("Return observation was not available at the review date")
    ret, cost = number(result.get("total_return_pct")), number(result.get("transaction_cost_bps"))
    if ret is None or ret < -100 or cost is None or cost < 0 or not result.get("source_url") or result.get("currency") != decision.get("mandate", {}).get("base_currency"):
        issues.append("Missing valid total return, costs, base currency or provenance")
    return issues


def shadow_returns(decision: dict, returns: list[dict], *, as_of: str | None = None) -> dict:
    """Compare frozen allocations using base-currency total returns, not price changes."""
    rows = {asset_key(r.get("asset_class")): r for r in returns}
    contributions, issues, periods = [], [], set()
    as_of = as_of or utc_now()
    if len(rows) != len(returns):
        issues.append("Duplicate return records")
    for allocation in decision["funding"]["rows"]:
        if allocation.get("current_pct") == 0 and allocation.get("target_pct") == 0:
            continue
        result = rows.get(asset_key(allocation["asset_class"]), {})
        ret = number(result.get("total_return_pct"))
        cost = number(result.get("transaction_cost_bps"))
        start, end = timestamp(result.get("from")), timestamp(result.get("to"))
        invalid = return_record_issues(decision, result, as_of)
        if invalid:
            issues.extend(f"{allocation['asset_class']}: {issue}" for issue in invalid)
            continue
        periods.add((start, end))
        old, new = number(allocation["current_pct"]), number(allocation["target_pct"])
        if old is None or new is None:
            issues.append("Unresolved allocation")
            continue
        contributions.append({"asset_class": allocation["asset_class"], "hold_pp": old * ret / 100,
                              "proposal_pp": new * ret / 100 - abs(new - old) * cost / 10000})
    if len(periods) != 1:
        issues.append("Return periods are not aligned")
    if decision["funding"]["status"] != "balanced":
        issues.append("Allocation is not funded")
    benchmark_name = decision.get("mandate", {}).get("benchmark")
    benchmark = rows.get(asset_key(benchmark_name), {})
    benchmark_valid = bool(benchmark) and not return_record_issues(decision, benchmark, as_of) and (timestamp(benchmark.get("from")), timestamp(benchmark.get("to"))) in periods
    proposed = sum(r["proposal_pp"] for r in contributions) if not issues else None
    benchmark_return = number(benchmark.get("total_return_pct")) if benchmark_valid and not issues else None
    return {"status": "measured" if not issues else "incomplete", "issues": issues, "contributions": contributions,
            "benchmark": {"name": benchmark_name, "status": "measured" if benchmark_return is not None else "unassessed",
                          "return_pct": benchmark_return, "excess_return_pp": proposed - benchmark_return if benchmark_return is not None else None},
            "hold_return_pct": sum(r["hold_pp"] for r in contributions) if not issues else None,
            "proposal_return_pct": sum(r["proposal_pp"] for r in contributions) if not issues else None,
            "decision_hash": decision["decision_hash"], "drawdown": shadow_drawdowns(decision, returns, as_of=as_of) if not issues else {"status": "unassessed", "issues": issues},
            "one_way_turnover_pct": decision["funding"]["one_way_turnover_pct"]}


def shadow_drawdowns(decision: dict, returns: list[dict], *, as_of: str | None = None) -> dict:
    series = {asset_key(row.get("asset_class")): row for row in returns}
    curves, issues = [], []
    as_of = as_of or utc_now()
    for weight in decision["funding"]["rows"]:
        if weight.get("current_pct") == 0 and weight.get("target_pct") == 0:
            continue
        source = series.get(asset_key(weight["asset_class"]), {})
        invalid = return_record_issues(decision, source, as_of)
        if invalid:
            issues.extend(invalid)
            continue
        points = source.get("cumulative_total_returns") or []
        if not points or source.get("currency") != decision["mandate"].get("base_currency") or not source.get("source_url"):
            issues.append(f"Dated cumulative total-return series missing for {weight['asset_class']}")
            continue
        dates = [timestamp(row.get("date")) for row in points if isinstance(row, dict)]
        values = [number(row.get("return_pct")) for row in points]
        cost = number(source.get("transaction_cost_bps"))
        if len(dates) != len(points) or any(date is None for date in dates) or dates != sorted(set(dates)) or any(value is None or value < -100 for value in values) or cost is None or cost < 0 or weight.get("target_pct") is None or weight.get("current_pct") is None:
            issues.append("Invalid dated return series, costs or allocation")
            continue
        if len(points) < 2 or dates[0] != timestamp(source.get("from")) or dates[-1] != timestamp(source.get("to")) or abs(values[0]) > 1e-8 or abs(values[-1] - number(source.get("total_return_pct"))) > 1e-6:
            issues.append("Drawdown series must span the return period, start at zero and agree with the reported total return")
            continue
        curves.append((dates, values, weight, cost))
    if not curves or issues or any(row[0] != curves[0][0] for row in curves) or decision["funding"]["status"] != "balanced":
        return {"status": "unassessed", "issues": issues or ["Return series are not aligned or allocation is unresolved"]}
    paths = []
    for index, date in enumerate(curves[0][0]):
        old = sum(row[2]["current_pct"] * row[1][index] / 100 for row in curves)
        new = sum(row[2]["target_pct"] * row[1][index] / 100 - abs(row[2]["trade_pct"]) * row[3] / 10000 for row in curves)
        paths.append({"date": date.isoformat(), "hold_return_pct": old, "proposal_return_pct": new})
    def drawdown(key):
        peak, worst = 1.0, 0.0
        for row in paths:
            level = 1 + row[key] / 100
            peak = max(peak, level)
            worst = min(worst, (level / peak - 1) * 100)
        return worst
    return {"status": "measured", "hold_max_drawdown_pct": drawdown("hold_return_pct"),
            "proposal_max_drawdown_pct": drawdown("proposal_return_pct"), "path": paths,
            "method": "Buy-and-hold, cumulative total returns in base currency, initial trading costs; no rebalancing"}


def forecast_calibration(forecasts: list[dict], observations: list[dict], as_of: str) -> dict:
    scores = []
    for forecast in forecasts:
        if not isinstance(forecast, dict):
            continue
        deadline = timestamp(forecast.get("deadline"))
        probability = number(forecast.get("probability"))
        if not deadline or not timestamp(as_of) or deadline > timestamp(as_of) or probability is None or not 0 <= probability <= 1:
            scores.append({"id": forecast.get("id"), "status": "unassessed"})
            continue
        outcome = evaluate_conditions([forecast], observations, deadline.isoformat())[0]
        assessed = outcome["status"] in {"triggered", "not_triggered"}
        scores.append({"id": forecast.get("id"), "status": "scored" if assessed else "unassessed",
                       "brier_score": (probability - int(outcome["status"] == "triggered")) ** 2 if assessed else None,
                       "outcome": outcome})
    completed = [row["brier_score"] for row in scores if row.get("brier_score") is not None]
    return {"forecasts": scores, "scored_count": len(completed), "mean_brier_score": sum(completed) / len(completed) if completed else None}
