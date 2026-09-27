"""Decision-level research, correction accounting and non-destructive quality checks."""

from copy import deepcopy
import re

from .portfolio_decisions import asset_key, number, supplied, funding_ledger, scenario_comparison, evaluate_conditions
from .portfolio_runtime import digest
from .portfolio_evidence import fact_observation_is_supported


def prepare_reviews(reviews):
    result = deepcopy(reviews)
    seen = set()
    for review in result:
        for finding in review.get("findings") or []:
            if isinstance(finding, dict):
                if not isinstance(finding.get("id"), str) or not finding["id"] or finding["id"] in seen:
                    finding["id"] = "finding_" + digest({"role": review.get("council_lane"),
                        "finding": {key: value for key, value in finding.items() if key not in {"id", "revision"}},
                        "duplicate": len(seen) if isinstance(finding.get("id"), str) and finding["id"] in seen else None})[:16]
                seen.add(finding["id"])
                finding["revision"] = digest({k: v for k, v in finding.items() if k not in {"id", "revision"}})
    return result


def research_questions(ideal, current, reviews, provisional, evidence=None, *, include_play_questions=True):
    questions = []
    for source in [ideal, current, *reviews, provisional]:
        for row in source.get("market_questions") or []:
            if isinstance(row, dict) and (include_play_questions or not row.get("play_ids")):
                questions.append({**row, "kind": "market_fact", "status": "unanswered",
                                  "origin": source.get("council_lane", "proposal")})
        for play in source.get("play_assessments") or []:
            if not include_play_questions or play.get("assessment_mode") == "brief":
                continue
            for leg in play.get("legs") or []:
                question = leg.get("unanswered_question")
                if isinstance(question, str) and question.strip() and play.get("play_id"):
                    questions.append({"question": question, "kind": "market_fact", "status": "unanswered",
                        "play_ids": [play["play_id"]], "asset_classes": [leg.get("expression") or leg.get("name")],
                        "material_reason": leg.get("portfolio_action") or leg.get("mechanism") or play.get("reason"),
                        "reuse_assessment": leg.get("pricing") or "This component remains unresolved in the saved review.",
                        "existing_fact_ids": leg.get("fact_ids") or [], "decision_impact": "high",
                        "origin": source.get("council_lane", "proposal")})
    known = {row["id"] for row in (evidence or {}).get("facts", [])}
    dispositions = {str(row.get("question", "")).casefold().rstrip("?. "): row
                    for row in provisional.get("research_dispositions") or [] if isinstance(row, dict)}
    for row in questions:
        answer = dispositions.get(str(row.get("question", "")).casefold().rstrip("?. "), {})
        refs = answer.get("fact_ids") or []
        if answer.get("reason") and (answer.get("status") == "not_market" or
                answer.get("status") == "answered" and refs and all(ref in known for ref in refs)):
            row.update(status=answer["status"], reuse_resolution=deepcopy(answer))
    return questions


def question_priority(row):
    return ({"high": 0, "medium": 1, "low": 2}.get(row.get("decision_impact"), 1),
            0 if row.get("play_ids") else 1)


def disposition_issues(proposal, reviews):
    dispositions = {row.get("finding_id"): row for row in proposal.get("review_dispositions") or [] if isinstance(row, dict)}
    issues = []
    for review in reviews:
        if review.get("stage_status") == "failed":
            continue
        for finding in review.get("findings") or []:
            decision = dispositions.get(finding.get("id"), {})
            checked = next((row for row in proposal.get("finding_checks", [])
                            if row.get("finding_id") == finding.get("id")), {})
            verified = checked.get("status") == "resolved" and checked.get("reason") and checked.get("fact_ids")
            try:
                text = proposal
                for key in checked.get("path") or []:
                    text = text[key]
                verified = verified and isinstance(text, str) and bool(checked.get("quote")) and checked["quote"] in text
            except (KeyError, IndexError, TypeError):
                verified = False
            if (decision.get("status") not in {"accepted", "rebutted"} or not decision.get("reason") or
                    finding.get("kind") == "factual_correction" and not verified):
                issues.append({"finding_id": finding.get("id"), "asset_class": finding.get("asset_class"),
                    "kind": finding.get("kind"), "detail": finding.get("argument"), "status": "unresolved"})
    return issues


def measurement_issues(left, right):
    missing, different = [], []
    for key in ("unit", "currency", "observed_at"):
        if not supplied(left.get(key)) or not supplied(right.get(key)):
            missing.append(key)
        elif left[key] != right[key]:
            different.append(key)
    measurements = [fact.get("measurement") or {} for fact in (left, right)]
    if not all(any(supplied(value) and value != "not_applicable" for value in row.values()) for row in measurements):
        missing.append("measurement basis")
    for key in ("reference_period", "annualization", "horizon_months", "price_basis", "inflation_index"):
        a, b = (row.get(key) for row in measurements)
        if a is None and b is None:
            continue
        if not supplied(a) or not supplied(b):
            missing.append(key)
        elif a != b:
            different.append(key)
    return missing, different


def financial_comparison_issues(proposal, evidence):
    facts = {row["id"]: row for row in evidence.get("facts", [])}
    issues = []
    for comparison in proposal.get("financial_comparisons") or []:
        left, right = (facts.get(comparison.get(key)) for key in ("left_fact_id", "right_fact_id"))
        if left is None or right is None:
            issues.append({**comparison, "status": "unresolved", "detail": "A comparison references unavailable evidence."})
            continue
        if comparison.get("operation"):
            problems = calculation_issues(left, right, comparison["operation"])
            if problems:
                issues.append({**comparison, "status": "requires_review" if comparison.get("adjustment") else "not_comparable",
                               "detail": "; ".join(problems)})
            continue
        missing, dimensions = measurement_issues(left, right)
        dimensions.extend(key for key in ("metric", "benchmark") if left.get(key) != right.get(key))
        if dimensions:
            issues.append({**comparison, "status": "requires_review" if comparison.get("adjustment") else "not_comparable",
                           "detail": "Different " + ", ".join(key.replace("_", " ") for key in dimensions)})
        if missing:
            issues.append({**comparison, "status": "unresolved", "detail": "Not established for both observations: " + ", ".join(missing)})
    return issues


def substantive_details(row):
    case = row.get("investment_case") or {}
    return any(isinstance(case.get(key), str) and supplied(case[key]) for key in
               ("why_better_than_hold", "why_better_than_cash", "downside"))


def linked_facts(value):
    if isinstance(value, dict):
        direct = {value[key] for key in ("left_fact_id", "right_fact_id", "fact_id") if isinstance(value.get(key), str)}
        return direct | {ref for field in ("fact_ids", "challenged_fact_ids") for ref in value.get(field) or [] if isinstance(ref, str)} | set().union(
            *(linked_facts(item) for key, item in value.items() if key not in {"fact_ids", "challenged_fact_ids", "previous_investment_details"}))
    if isinstance(value, list):
        return set().union(*(linked_facts(item) for item in value))
    return set()


def resolve_fact_aliases(value, evidence):
    aliases = evidence.get("fact_aliases") or {}
    result = deepcopy(value)
    def visit(item):
        if isinstance(item, dict):
            for key, child in item.items():
                if key in {"fact_ids", "challenged_fact_ids"} and isinstance(child, list):
                    item[key] = list(dict.fromkeys(aliases.get(ref, ref) for ref in child if isinstance(ref, str)))
                elif key in {"fact_id", "left_fact_id", "right_fact_id"} and isinstance(child, str):
                    item[key] = aliases.get(child, child)
                else:
                    visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)
    visit(result)
    return result


def detail_basis(row, evidence=None):
    fields = ("asset_class", "target_pct", "min_pct", "max_pct", "purpose", "rationale", "thesis_role",
              "investment_case_summary", "fact_ids", "contrary_evidence", "research_question_ids")
    basis = {key: row.get(key) for key in fields}
    if evidence is not None:
        from .portfolio_tasks import evidence_for_decisions
        packet = evidence_for_decisions(evidence, row)
        basis["evidence"] = {"contract": "case-dependencies-v2",
            "facts": sorted(packet.get("facts", []), key=lambda item: item["id"]),
            "questions": sorted(packet.get("research_questions", []), key=lambda item: item.get("question_id", "")),
            "sources": sorted(packet.get("sources", []), key=lambda item: item["id"]),
            "missing_fact_ids": packet.get("evidence_scope", {}).get("missing_fact_ids", [])}
    return digest(basis)


DETAIL_FIELDS = ("implementation", "market_pricing", "investment_case", "alternatives")


def record_authored_details(proposal, response, evidence):
    """Version only cases actually written in this response, not inherited cases."""
    authored = {asset_key(row.get("asset_class")): row["investment_case"] for row in response.get("target_updates", [])
                if row.get("investment_case")}
    for row in proposal.get("asset_class_targets", []):
        if row.get("investment_case") and row["investment_case"] == authored.get(asset_key(row.get("asset_class"))):
            row["detail_origin"] = "final_synthesis"
            row["detail_status"] = "current" if substantive_details(row) else "needs_review"
            row["detail_evidence_hash"] = detail_basis(row, evidence)


def retain_current_details(final, details, evidence=None):
    result = deepcopy(final)
    prior = {asset_key(row.get("asset_class")): row for row in details.get("asset_class_targets") or []}
    stale = []
    for row in result.get("asset_class_targets") or []:
        previous = prior.get(asset_key(row.get("asset_class")))
        if row.get("detail_origin") == "final_synthesis" and row.get("investment_case"):
            unchanged = evidence is not None and row.get("detail_evidence_hash") == detail_basis(row, evidence)
            row["detail_status"] = "current" if unchanged and substantive_details(row) else "needs_review"
            row["detail_reuse_reason"] = "synthesis_case_matches" if unchanged else "synthesis_case_requires_review"
            continue
        if (evidence is not None and row.get("detail_status") == "current" and substantive_details(row)
                and row.get("detail_evidence_hash") == detail_basis(row, evidence)):
            row["detail_reuse_reason"] = "unchanged_decision_and_case_evidence"
            continue
        evidence_unchanged = evidence is None or previous and previous.get("detail_evidence_hash") == detail_basis({**row, **previous}, evidence)
        expression_unchanged = previous and all(not row.get(key) or row[key] == previous.get(key) for key in DETAIL_FIELDS)
        prior_basis = (previous.get("detail_decision_hash") or detail_basis(previous)) if previous else None
        if previous and expression_unchanged and evidence_unchanged and prior_basis == detail_basis(row):
            for key in DETAIL_FIELDS:
                if key not in row and key in previous:
                    row[key] = deepcopy(previous[key])
            row["detail_status"] = "current" if substantive_details(row) else "needs_review"
            row["detail_reuse_reason"] = "saved_case_matches" if row["detail_status"] == "current" else "saved_case_incomplete"
            if row["detail_status"] == "current" and evidence is not None:
                row["detail_evidence_hash"] = detail_basis(row, evidence)
        else:
            row["detail_reuse_reason"] = ("no_saved_case" if previous is None else
                "investment_expression_changed" if not expression_unchanged else
                "case_evidence_changed" if not evidence_unchanged else "allocation_or_rationale_changed")
            previous_details = {key: row.pop(key) for key in ("market_pricing", "investment_case", "alternatives") if key in row}
            if previous_details:
                row["previous_investment_details"] = previous_details
            row.pop("detail_evidence_hash", None)
            row["detail_status"] = "needs_review"
            stale.append(row)
    return result, stale


def implementation_comparison(snapshot, proposal, evidence):
    """Compare recorded alternatives; never infer sensitivities or invent a trade plan."""
    destination = funding_ledger(snapshot, proposal)
    alternative = materialize_retained_weights(snapshot, proposal.get("smaller_change_alternative") or {})
    smaller = funding_ledger(snapshot, alternative) if alternative.get("asset_class_targets") else None
    issues = [f"{row['asset_class']}: {row['reason']} ({row['source']})" for row in destination.get("funding_flow_issues", [])]
    if smaller:
        issues.extend(smaller.get("issues", []))
        issues.extend(f"Smaller-change {row['asset_class']}: {row['reason']} ({row['source']})"
                      for row in smaller.get("funding_flow_issues", []))
        a, b = smaller.get("one_way_turnover_pct"), destination.get("one_way_turnover_pct")
        if a is None or b is None:
            issues.append("The lower-turnover comparison cannot be established from the recorded holdings and targets.")
        elif a > b:
            issues.append(f"The alternative has greater turnover ({a:g}%) than the destination ({b:g}%).")
    scenarios, exposures = snapshot.get("scenarios") or [], snapshot.get("risk_exposures") or {}
    def assess(ledger):
        calculated = scenario_comparison({"funding": ledger, "mandate": snapshot.get("mandate") or {}}, scenarios, exposures)
        known = {row["id"] for row in evidence.get("facts", [])}
        qualitative = []
        for scenario in proposal.get("scenario_risks", []):
            effects = {asset_key(row.get("asset_class")): row for row in scenario.get("exposures", [])}
            assumptions = deepcopy(scenario.get("assumptions") or [])
            for assumption in assumptions:
                refs = assumption.get("fact_ids") or []
                assumption["reference_status"] = "linked_not_independently_verified" if refs and set(refs) <= known else "hypothetical" if assumption.get("basis") == "hypothetical" else "unresolved"
            qualitative.append({"name": scenario.get("name"), "status": "qualitative", "mechanism": scenario.get("mechanism"),
                "horizon": scenario.get("horizon"), "assumptions": assumptions,
                "rows": [{"asset_class": row["asset_class"], "current_pct": row["current_pct"], "target_pct": row["target_pct"],
                    "direction": effects.get(asset_key(row["asset_class"]), {}).get("direction", "unknown"),
                    "reason": effects.get(asset_key(row["asset_class"]), {}).get("reason", "No scenario assessment supplied"),
                    "return_pct": None} for row in ledger["rows"]],
                "hold_return_pct": None, "proposed_return_pct": None,
                "method": "Qualitative causal comparison; weights are recorded allocations, not estimated losses or correlations"})
        by_name = {asset_key(row.get("name")): row for row in qualitative}
        for numerical in calculated:
            context = by_name.pop(asset_key(numerical.get("name")), None)
            if not context:
                continue
            effects = {asset_key(row["asset_class"]): row for row in context["rows"]}
            for row in numerical["rows"]:
                effect = effects.get(asset_key(row["asset_class"]), {})
                row.update({key: effect[key] for key in ("direction", "reason") if key in effect})
            numerical["numerical_status"] = numerical["status"]
            numerical["qualitative_assessment"] = {key: value for key, value in context.items()
                                                  if key not in {"rows", "status", "hold_return_pct", "proposed_return_pct"}}
            if numerical["status"] != "calculated":
                numerical["status"] = "mixed" if any(row.get("return_pct") is not None for row in numerical["rows"]) else "qualitative"
        return [*calculated, *by_name.values()]
    observations = list(snapshot.get("review_observations") or [])
    sources = {row.get("id"): row for row in (evidence.get("source_packet") or {}).get("sources", [])}
    for fact in evidence.get("facts", []):
        if (number(fact.get("value")) is not None and fact.get("source_ids") and fact.get("observed_at")
                and fact.get("kind") in {"market_price", "observed_macro"}
                and fact_observation_is_supported(fact)):
            url = next((sources[ref].get("url") for ref in fact["source_ids"] if ref in sources and sources[ref].get("url")), None)
            observations.append({**fact, "as_of": fact["observed_at"], "fact_id": fact.get("id"), "source_url": url})
    forecasts = [{**deepcopy(row), "kind": "allocation_intent" if row.get("kind") == "allocation_intent" or
        re.search(r"portfolio weight|allocation|target weight", str(row.get("metric") or ""), re.I) else "market_forecast"}
        for row in proposal.get("forecasts") or [] if isinstance(row, dict)]
    destination_scenarios = assess(destination)
    statuses = {row["status"] for row in destination_scenarios}
    return {"destination": {"funding": destination, "scenarios": destination_scenarios},
            "smaller_change": {"funding": smaller, "scenarios": assess(smaller)} if smaller else None,
            "smaller_change_proposal": alternative,
            "choice": proposal.get("implementation_choice") or {},
            "issues": issues,
            "scenario_status": next(iter(statuses)) if len(statuses) == 1 else "mixed" if statuses else "No scenario assumptions supplied; outcomes remain unknown.",
            "holdings_status": "holding-level context supplied" if snapshot.get("positions") else "Allocation-level comparison; individual holding risks and tax lots are not established.",
            "review_conditions": evaluate_conditions(proposal.get("monitoring_triggers") or [],
                observations, (evidence.get("source_packet") or {}).get("as_of") or snapshot.get("as_of")),
            "forecasts": [row for row in forecasts if row["kind"] == "market_forecast"],
            "allocation_intentions": [row for row in forecasts if row["kind"] == "allocation_intent"]}


def materialize_retained_weights(snapshot, alternative):
    result = deepcopy(alternative)
    if result.get("retain_unmentioned") is not True:
        return result
    # Explicit HOLD actions also cover residual capital after declared partial-overlap mappings.
    actions = {asset_key(row.get("asset_class")): row for row in result.get("current_sleeve_actions") or []}
    current = [*snapshot.get("asset_classes", [])]
    if not any(asset_key(row.get("asset_class")) == "CASH" for row in current):
        current.append({"asset_class": "CASH", "portfolio_pct": (snapshot.get("portfolio") or {}).get("cash_pct")})
    for row in current:
        actions.setdefault(asset_key(row.get("asset_class")), {"asset_class": row["asset_class"], "action": "HOLD",
            "target_pct": row.get("portfolio_pct"), "rationale": "Retain the recorded current weight under the explicit smaller-change policy."})
    result["current_sleeve_actions"] = list(actions.values())
    return result


def common_scenario_comparison(snapshot, ideal, final, evidence):
    """Use one scenario definition for all four shapes; unknowns stay unknown."""
    from .portfolio_exposures import reference_links
    rows = [{"asset_class": row["asset_class"], "target_pct": row.get("portfolio_pct"),
             "position_identity": "existing"} for row in snapshot.get("asset_classes", [])]
    if not any(asset_key(row["asset_class"]) == "CASH" for row in rows):
        rows.append({"asset_class": "cash", "target_pct": (snapshot.get("portfolio") or {}).get("cash_pct")})
    views = {"current": {"asset_class_targets": rows}, "independent_ideal": ideal,
             "smaller_change": materialize_retained_weights(snapshot, final.get("smaller_change_alternative") or {}),
             "final": final}
    definitions = [{**deepcopy(row), "id": "scenario_" + digest(row)[:16]}
                   for row in {digest(row): row for row in final.get("scenario_risks") or []}.values()]
    supported = {row["id"] for row in evidence.get("facts", []) if fact_observation_is_supported(row)}
    known = {row["id"] for row in evidence.get("facts", [])}
    for definition in definitions:
        for assumption in definition.get("assumptions", []):
            refs = set(assumption.get("fact_ids") or [])
            assumption["reference_status"] = ("source_supported" if refs and refs <= supported else
                "linked_not_verified" if refs and refs <= known else
                "hypothetical" if assumption.get("basis") == "hypothetical" else "unresolved")
    output = {}
    for name, candidate in views.items():
        if not candidate.get("asset_class_targets"):
            output[name] = {"status": "not_supplied", "scenarios": []}
            continue
        ledger = funding_ledger(snapshot, candidate)
        weights = [{"asset_class": row["asset_class"], "target_pct": row["target_pct"]} for row in ledger["rows"]]
        view = "ideal" if name == "independent_ideal" else "holdings" if name == "current" else None
        source_rows = ideal.get("asset_class_targets", []) if view == "ideal" else snapshot.get("asset_classes", [])
        equivalents, mapping_issues = reference_links(final, view, source_rows) if view else ({}, [])
        scenarios = []
        for definition in definitions:
            effects = {asset_key(row.get("asset_class")): row.get("direction") for row in definition.get("exposures", [])}
            totals = {key: 0.0 for key in ("benefit", "harm", "mixed", "unknown")}
            mappings = []
            for row in weights:
                weight = number(row.get("target_pct"))
                if weight is not None:
                    key = asset_key(row["asset_class"])
                    effect = effects.get(key)
                    via = []
                    if effect is None:
                        # This maps qualitative direction onto the source's OWN
                        # weight. It never transfers capital or substitutes instruments.
                        via = [target for target, links in equivalents.items()
                            if any(link["source_key"] == key and link["relationship"] == "equivalent" for link in links)]
                        directions = {effects.get(asset_key(target)) for target in via} - {None}
                        if len(directions) == 1:
                            effect = next(iter(directions))
                    mappings.append({"asset_class": row["asset_class"], "direction": effect or "unknown",
                        "basis": "declared_equivalence" if via and effect else "direct" if effect else "unmapped",
                        "related_exposures": via})
                    totals[effect if effect in totals else "unknown"] += weight
            scenarios.append({"scenario_id": definition["id"], "status": "qualitative",
                "directional_weight_pct": {key: round(value, 6) for key, value in totals.items()},
                "exposure_mapping": mappings,
                "proposed_return_pct": None})
        output[name] = {"status": "recorded", "weights": weights, "scenarios": scenarios,
            "mapping_issues": mapping_issues,
            "funding": {key: ledger.get(key) for key in ("status", "specified_target_total_pct", "one_way_turnover_pct", "issues")}}
    return {"contract": "common-scenarios-v1", "definitions": definitions, "views": output,
        "limitations": ["Directional exposures are not portfolio return estimates. Missing sensitivities and instrument mappings remain unknown."]}


def _curve(fact):
    measurement = fact.get("measurement") or {}
    if measurement.get("curve"):
        return str(measurement["curve"]).casefold()
    benchmark = str(fact.get("benchmark") or "").casefold()
    return re.sub(r"[^a-z]", "", re.sub(r"\b\d+(?:\.\d+)?\s*[- ]?\s*(?:years?|yrs?|months?|mos?|[ym])\b", "", benchmark))


def calculation_issues(left, right, operation):
    """Check dimensions according to the operation, not identical metric labels."""
    missing, different = measurement_issues(left, right)
    a, b = left.get("measurement") or {}, right.get("measurement") or {}
    problems = []
    if operation in {"curve_spread", "breakeven_spread"}:
        if not all("yield" in str(row.get("metric", "")).lower() for row in (left, right)):
            problems.append("Both inputs must be identified yields.")
        issuer_match = bool(a.get("issuer") and a.get("issuer") == b.get("issuer") and left.get("currency") == right.get("currency"))
        if not issuer_match and (not _curve(left) or _curve(left) != _curve(right)):
            problems.append("The observations do not establish a common yield curve.")
        if operation == "curve_spread":
            different = [field for field in different if field != "horizon_months"]
        else:
            if a.get("price_basis") != "nominal" or b.get("price_basis") != "real":
                problems.append("Inflation compensation requires nominal yield minus real yield.")
            maturity_a = a.get("maturity_months") or a.get("horizon_months")
            maturity_b = b.get("maturity_months") or b.get("horizon_months")
            if not maturity_a or maturity_a != maturity_b:
                problems.append("Nominal and real yields require the same established maturity.")
            different = [field for field in different if field in {"unit", "currency", "observed_at", "reference_period", "annualization"}]
            missing = [field for field in missing if field != "horizon_months" or not maturity_a or not maturity_b]
        missing = [field for field in missing if field not in {"measurement basis", "inflation_index"}]
    else:
        if not supplied(left.get("metric")) or left.get("metric") != right.get("metric"):
            problems.append("The observations do not establish the same economic measure.")
        if not supplied(left.get("benchmark")) or left.get("benchmark") != right.get("benchmark"):
            problems.append("The observations do not establish the same benchmark or instrument.")
        if operation == "time_change":
            different = [field for field in different if field not in {"observed_at", "reference_period"}]
        elif operation != "revision_change" and left.get("vintage") != right.get("vintage"):
            problems.append("Different release vintages require an explicit revision comparison.")
    if missing:
        problems.append("Not established: " + ", ".join(missing))
    if different:
        problems.append("Incompatible " + ", ".join(different))
    return problems


def calculate_financial_claims(proposal, evidence, snapshot=None):
    """Arithmetic uses recorded numeric facts. It never supplies missing market inputs."""
    facts = {row["id"]: row for row in evidence.get("facts", [])}
    results = []
    for claim in proposal.get("calculations") or []:
        if not isinstance(claim, dict):
            continue
        if claim.get("operation") == "allocation_change":
            rows = funding_ledger(snapshot, proposal)["rows"] if snapshot is not None else []
            row = next((row for row in rows if asset_key(row["asset_class"]) == asset_key(claim.get("target_id"))), {})
            value = row.get("trade_pct")
            results.append({**claim, "computed_value": value, "unit": "percentage_points", "fact_ids": [],
                "operands": {"position_id": row.get("asset_class"), "current_pct": row.get("current_pct"), "target_pct": row.get("target_pct")},
                "status": "calculated" if value is not None else "unresolved", "limitation": None if value is not None else "Recorded allocation identity is unavailable"})
            continue
        operands = [facts.get(ref) for ref in claim.get("fact_ids") or []]
        values = [number(row.get("value")) if row else None for row in operands]
        error, value = None, None
        if len(values) != 2 or any(item is None for item in values):
            error = "Two recorded numeric observations are required."
        elif calculation_issues(*operands, claim.get("operation")):
            error = "; ".join(calculation_issues(*operands, claim.get("operation")))
        elif claim.get("operation") == "midpoint":
            value = sum(values) / 2
        elif claim.get("operation") in {"time_change", "revision_change"}:
            from .portfolio_evidence import timestamp
            field = "observed_at" if claim["operation"] == "time_change" else "published_at"
            dates = [timestamp(row.get(field)) for row in operands]
            if not all(dates) or dates[0] == dates[1]:
                error = f"Distinct recorded {field} dates are required to establish chronological change."
            else:
                later = 0 if dates[0] > dates[1] else 1
                value = round(values[later] - values[1 - later], 12)
                claim = {**claim, "calculation_order": {"from_fact_id": operands[1 - later]["id"],
                                                       "to_fact_id": operands[later]["id"]}}
        elif claim.get("operation") in {"difference", "curve_spread", "breakeven_spread"}:
            value = round(values[0] - values[1], 12)
        else:
            error = "Unsupported calculation; retain the stated assumptions for review."
        unit = operands[0].get("unit") if operands and operands[0] else None
        percentage_difference = claim.get("operation") != "midpoint" and str(unit).lower() in {"%", "percent", "pct"}
        results.append({**claim, "computed_value": value, "status": "calculated" if value is not None else "unresolved",
                        "limitation": error, "unit": "percentage_points" if percentage_difference else unit,
                        "basis_points": round(value * 100, 8) if value is not None and percentage_difference else None})
    return results


def play_outcomes(proposal):
    """Use recorded links, not asset-name guesses, to explain partial adoption."""
    result = deepcopy(proposal)
    targets = {asset_key(row.get("asset_class")): row for row in result.get("asset_class_targets") or []}
    for play in result.get("play_assessments") or []:
        play["adopted_allocations"] = []
        play["unresolved_exposure_links"] = []
        for name in dict.fromkeys(name for name in play.get("selected_exposures") or [] if isinstance(name, str) and name.strip()):
            row = targets.get(asset_key(name))
            if row is None:
                play["unresolved_exposure_links"].append(name)
            elif (number(row.get("target_pct")) or 0) > 0:
                play["adopted_allocations"].append({key: row.get(key) for key in ("asset_class", "display_name", "target_pct")})
        if not play.get("allocation_effect"):
            play["allocation_effect"] = play.get("portfolio_action") or "The allocation effect has not been explained."
    return result


def judgment_audit(proposal, reviews, evidence):
    known = {row["id"] for row in evidence.get("facts", [])}
    supported = {row["id"] for row in evidence.get("facts", []) if fact_observation_is_supported(row)}
    checked = deepcopy(proposal)
    checked["finding_checks"] = [row for row in proposal.get("finding_checks", [])
                                 if row.get("fact_ids") and all(ref in supported for ref in row["fact_ids"])]
    return {"unresolved_findings": disposition_issues(checked, reviews),
            "comparison_issues": financial_comparison_issues(proposal, evidence),
            "exposure_mapping_issues": proposal.get("comparison_issues") or [],
            "missing_fact_ids": sorted(linked_facts(proposal) - known),
            "contributors": [{"role": row.get("council_lane"), "model": row.get("model"),
                "contributed": row.get("stage_status") == "complete" and bool(row.get("findings") or row.get("summary")),
                "error": row.get("error") or None} for row in reviews]}


def decision_checks(snapshot, proposal, reviews, evidence):
    proposal = {key: value for key, value in proposal.items()
                if key not in {"judgment_audit", "computed_claims", "implementation_comparison"}}
    return {"judgment_audit": {**judgment_audit(proposal, reviews, evidence),
                              "financial_case_issues": financial_case_issues(proposal, evidence),
                              "play_expression_issues": play_expression_issues(proposal),
                              "action_basis_issues": action_basis_issues(snapshot, proposal),
                              "funding_flow_issues": funding_ledger(snapshot, proposal).get("funding_flow_issues", [])},
            "computed_claims": calculate_financial_claims(proposal, evidence, snapshot),
            "implementation_comparison": implementation_comparison(snapshot, proposal, evidence)}


def financial_case_issues(proposal, evidence):
    """Assess the recorded argument, never turn unknown economics into a sell signal."""
    facts = {row["id"]: row for row in evidence.get("facts", [])}
    issues = []
    for target in proposal.get("asset_class_targets", []):
        if (number(target.get("target_pct")) or 0) <= 0:
            continue
        case = target.get("investment_case") or {}
        refs = linked_facts(target)
        changed = sorted(ref for ref in refs if ref in facts and (
            facts[ref].get("superseded_by") or facts[ref].get("claim_status") == "unsupported"))
        gaps = []
        if not supplied(case.get("sizing_tradeoff")):
            gaps.append("The proposed size has no recorded marginal benefit and opportunity-cost comparison.")
        chain = case.get("causal_chain") or []
        unknown_links = [row.get("link") for row in chain if row.get("basis") == "unresolved"]
        if not chain or unknown_links:
            gaps.append("The return mechanism remains incomplete. Missing economics is uncertainty, not evidence against this exposure.")
        if (changed or target.get("premise_update_required")) and not supplied(case.get("premise_update")):
            gaps.append("The investment premise changed; the retained or revised size needs an explicit new justification.")
        ungrounded = [row.get("link") for row in chain if row.get("basis") == "observed" and
                      (not row.get("fact_ids") or any(not fact_observation_is_supported(facts.get(ref, {})) for ref in row["fact_ids"]))]
        if ungrounded:
            gaps.append("A causal link is labelled observed without source-supported observations. Treat it as an assumption or unresolved, not an established return mechanism.")
        if gaps:
            issues.append({"asset_class": target.get("asset_class"), "target_pct": target.get("target_pct"),
                "status": "case_incomplete", "reasons": gaps, "changed_fact_ids": changed,
                "unknown_links": unknown_links, "unsubstantiated_observed_links": ungrounded,
                "weight_action": "Retain the proposal as a conditional judgment; do not infer a trade from missing evidence."})
    return issues


def play_expression_issues(proposal):
    """Check expression labels against this proposal's own exposure identities."""
    targets = {asset_key(row.get("asset_class")): row for row in proposal.get("asset_class_targets", [])}
    issues = []
    for play in proposal.get("play_assessments", []):
        for index, expression in enumerate(play.get("expressions") or []):
            target = targets.get(asset_key(expression.get("asset_class")))
            if not target:
                continue  # An unallocated alternative can legitimately introduce an exposure.
            labels = {asset_key(target.get("asset_class")), asset_key(target.get("display_name")),
                      *(asset_key(alias) for alias in target.get("aliases") or [])}
            label = asset_key(expression.get("display_name"))
            variants = [target.get("asset_class"), target.get("display_name"), *(target.get("aliases") or [])]
            if label and label not in labels and not any(_equity_label_variant(expression.get("display_name"), candidate) for candidate in variants):
                issues.append({"play_id": play.get("play_id"), "expression_index": index,
                    "asset_class": expression.get("asset_class"), "reported_label": expression.get("display_name"),
                    "target_label": target.get("display_name") or target.get("asset_class"), "status": "identity_needs_review",
                    "reason": "The expression label does not match its referenced exposure. Confirm the reference or declare an alias; do not treat the label as an allocation instruction."})
    return issues


def _equity_label_variant(left, right):
    # Only descriptive equity suffixes on the same miner/producer name qualify.
    # Never remove instrument words from a bullion/bond/equity comparison.
    def tokens(value):
        words = str(value or "").lower().replace("_", " ").split()
        return {word[:-1] if word in {"miners", "producers"} else word for word in words}
    a, b = tokens(left), tokens(right)
    core = a & b
    return bool(core & {"miner", "producer"}) and bool(core - {"miner", "producer"}) and (
        a ^ b <= {"equity", "equities", "shares", "stocks"})


def action_basis_issues(snapshot, proposal):
    """Surface unsupported actions for the existing reviewer; never impose a trade or a hold."""
    declared = {asset_key(row.get("asset_class")): row for row in [
        *proposal.get("current_sleeve_actions", []), *proposal.get("asset_class_targets", [])]}
    issues = []
    for row in funding_ledger(snapshot, proposal)["rows"]:
        basis = declared.get(asset_key(row["asset_class"]), {}).get("action_basis") or {}
        if abs(row.get("trade_pct") or 0) <= .05:
            continue
        valid = basis.get("category") in {"investment", "risk", "mandate", "liquidity"} and supplied(basis.get("reason"))
        if not valid or (basis.get("category") == "investment" and basis.get("evidence_status") == "unassessed"):
            issues.append({"asset_class": row["asset_class"], "action": row["reference_trade_action"],
                "reason": "The action needs an investment, risk, mandate or liquidity justification independent of missing research.",
                "reported_basis": deepcopy(basis)})
    return issues


def consistency_inputs(snapshot, ideal, current, final):
    """Compact recorded comparators for the reviewer, not another generated narrative."""
    fields = ("asset_class", "display_name", "target_pct", "purpose", "implementation", "liquidity_class")
    claims = final.get("computed_claims") or []
    from .portfolio_tasks import compact_decision_checks
    return {"baseline_allocations": {name: [{field: row[field] for field in fields if field in row}
        for row in proposal.get("asset_class_targets", [])] for name, proposal in (
            ("independent_ideal", ideal), ("current_aware", current), ("final", final))},
        "original_cash_pct": (snapshot.get("portfolio") or {}).get("cash_pct"),
        "action_basis_issues": action_basis_issues(snapshot, final),
        "financial_case_issues": (final.get("judgment_audit") or {}).get("financial_case_issues", []),
        "play_expression_issues": play_expression_issues(final),
        "common_scenario_comparison": final.get("common_scenario_comparison"),
        "calculation_counts": {"total": len(claims), "calculated": sum(row.get("status") == "calculated" for row in claims),
                               "unresolved": sum(row.get("status") != "calculated" for row in claims)},
        "funding": compact_decision_checks({"implementation_comparison": final.get("implementation_comparison")
            or implementation_comparison(snapshot, final, {})})["implementation_comparison"]}


def decision_revision_scope(proposal, review, snapshot=None):
    """Scope one reconsideration to challenged decisions and named funding legs."""
    reasons, assets = [], set()
    if snapshot is not None:
        from .portfolio_exposures import reference_links
        holdings = [*snapshot.get("asset_classes", [])]
        if not any(asset_key(row.get("asset_class")) == "CASH" for row in holdings):
            holdings.append({"asset_class": "cash", "portfolio_pct": (snapshot.get("portfolio") or {}).get("cash_pct")})
        alternatives = [("destination", proposal)]
        if (proposal.get("smaller_change_alternative") or {}).get("asset_class_targets"):
            alternatives.append(("smaller-change alternative", materialize_retained_weights(snapshot, proposal["smaller_change_alternative"])))
        for name, candidate in alternatives:
            funding = funding_ledger(snapshot, candidate)
            if not funding["issues"]:
                continue
            affected = {asset_key(row["asset_class"]) for row in funding["rows"] if row["status"] == "unresolved"}
            for target in candidate.get("asset_class_targets", []):
                _, errors = reference_links({"asset_class_targets": [target], "reconciliation": candidate.get("reconciliation", [])}, "holdings", holdings)
                if errors:
                    affected.add(asset_key(target["asset_class"]))
            if abs(funding["specified_target_total_pct"] - 100) > .05:
                affected.add("CASH")
                affected.update(asset_key(row["asset_class"]) for row in candidate.get("asset_class_targets", [])
                                if row.get("liquidity_class") in {"cash", "cash_equivalent"})
            if affected:
                assets.update(affected)
                reasons.append({"asset_classes": sorted(affected), "reason": f"Reconcile the {name} using the original holdings, without inventing equivalence or using cash as an unexplained plug.",
                                "funding_issues": funding["issues"]})
    for issue in (proposal.get("judgment_audit") or {}).get("action_basis_issues", []):
        if (issue.get("reported_basis") or {}).get("category") == "research_gap":
            assets.add(asset_key(issue["asset_class"]))
            reasons.append({"asset_classes": [issue["asset_class"]], "reason": issue["reason"]})
    for request in review.get("decision_revisions") or []:
        if not isinstance(request, dict) or not supplied(request.get("reason")):
            continue
        names = request.get("asset_classes") or []
        if not names:
            continue
        assets.update(asset_key(name) for name in [*names, *(request.get("funding_asset_classes") or [])] if name)
        reasons.append(request)
    for patch in proposal.get("claim_corrections") or []:
        path = patch.get("path") or []
        if len(path) > 2 and path[0] == "asset_class_targets" and type(path[1]) is int:
            row = proposal["asset_class_targets"][path[1]]
            assets.add(asset_key(row["asset_class"]))
            reasons.append({"asset_classes": [row["asset_class"]], "reason": patch["reason"]})
    if assets:
        # Cash is the existing funding alternative, never an invented balancing plug.
        assets.update(asset_key(row["asset_class"]) for row in proposal.get("asset_class_targets", [])
                      if asset_key(row["asset_class"]) == "CASH")
    return {"asset_classes": sorted(assets), "reasons": reasons}


def apply_decision_revision(proposal, response, scope, snapshot):
    """Apply only scoped, funded revisions; retain the whole original on bad patches."""
    result = deepcopy(proposal)
    allowed = set(scope.get("asset_classes") or [])
    errors = []
    if response.get("stage_status") != "complete" or not supplied(response.get("reason")):
        errors.append(response.get("error") or "Decision reconsideration did not return a completed explanation.")
    updates = response if not errors else {}
    from .portfolio_independent import TARGET_SCHEMA, HOLDING_SCHEMA
    for field in ("asset_class_targets", "current_sleeve_actions"):
        existing = {asset_key(row["asset_class"]): row for row in result.get(field, [])}
        seen = set()
        permitted = set(TARGET_SCHEMA) | set(DETAIL_FIELDS) | {"action", "positioning_stance"} if field == "asset_class_targets" else set(HOLDING_SCHEMA) | {"target_pct"}
        for row in updates.get("target_updates" if field == "asset_class_targets" else field) or []:
            if not isinstance(row, dict):
                errors.append("A decision revision is not an object.")
                continue
            key = asset_key(row.get("asset_class"))
            if not key or key not in allowed or key in seen:
                errors.append("A decision revision is outside the reviewed scope or duplicated.")
                continue
            seen.add(key)
            existing[key] = {**existing.get(key, {}), **{key: deepcopy(value) for key, value in row.items() if key in permitted}}
        result[field] = list(existing.values())
    before, after = funding_ledger(snapshot, proposal), funding_ledger(snapshot, result)
    if abs(after["specified_target_total_pct"] - 100) > .05 or set(after["issues"]) - set(before["issues"]):
        errors.append("The scoped revision does not establish a funded portfolio without new allocation errors.")
    affected_plays = {row["play_id"] for row in proposal.get("play_assessments", [])
                      if any(asset_key(name) in allowed for name in row.get("selected_exposures", []))}
    replacements = {}
    for row in updates.get("play_assessments") or []:
        if row.get("play_id") not in affected_plays or row["play_id"] in replacements:
            errors.append("A play revision is outside the affected decisions or duplicated.")
        else:
            replacements[row["play_id"]] = row
    result["play_assessments"] = [deepcopy(replacements.get(row["play_id"], row)) for row in proposal.get("play_assessments", [])]
    changed = any(result.get(field) != proposal.get(field) for field in ("asset_class_targets", "current_sleeve_actions"))
    if changed and not supplied(response.get("executive_summary")):
        errors.append("A changed decision needs a summary reflecting its settled weights.")
    if errors:
        result = deepcopy(proposal)
    else:
        if isinstance(response.get("implementation_choice"), dict):
            result["implementation_choice"] = {**result.get("implementation_choice", {}), **deepcopy(response["implementation_choice"])}
        if supplied(response.get("executive_summary")):
            result["executive_summary"] = response["executive_summary"]
        revised = {asset_key(row["asset_class"]): row for row in response.get("target_updates") or []}
        for comparison in result.get("reconciliation", []):
            row = revised.get(asset_key(comparison.get("asset_class")))
            if row and supplied(row.get("rationale")):
                comparison["decision"] = row["rationale"]
                comparison.pop("reason_for_departure", None)
        if isinstance(response.get("smaller_change_alternative"), dict):
            previous = proposal.get("smaller_change_alternative") or {}
            alternative = deepcopy(previous)
            update = response["smaller_change_alternative"]
            alternative_errors = []
            for field in ("asset_class_targets", "current_sleeve_actions"):
                existing = {asset_key(row["asset_class"]): row for row in previous.get(field, [])}
                for row in update.get(field) or []:
                    key = asset_key(row.get("asset_class"))
                    if key not in allowed and row != existing.get(key):
                        alternative_errors.append("Alternative revision changes an exposure outside the reviewed scope.")
                    else:
                        existing[key] = {**existing.get(key, {}), **deepcopy(row)}
                alternative[field] = list(existing.values())
            for field in ("retain_unmentioned", "rationale"):
                if field in update:
                    alternative[field] = deepcopy(update[field])
            alternative_errors.extend(funding_ledger(snapshot, materialize_retained_weights(snapshot, alternative))["issues"])
            if not alternative_errors:
                result["smaller_change_alternative"] = alternative
            else:
                result["alternative_revision_issues"] = list(dict.fromkeys(alternative_errors))
    result["decision_reconsideration"] = {"status": "unresolved" if errors else "reviewed", "scope": scope,
        "reason": response.get("reason"), "issues": errors,
        "before_hash": digest(proposal), "model": response.get("model"),
        "changed": not errors and any(result.get(field) != proposal.get(field) for field in ("asset_class_targets", "current_sleeve_actions"))}
    for row in result.get("asset_class_targets", []):
        if asset_key(row["asset_class"]) in allowed:
            row["decision_review_status"] = "unresolved" if errors else "reviewed"
    return result


PROSE_ROOTS = {"executive_summary", "strategic_view", "asset_class_targets", "play_assessments", "reconciliation", "implementation_choice", "commentary",
              "excluded_opportunities", "smaller_change_alternative", "implementation_notes", "risk_flags", "scenario_risks", "monitoring_triggers",
              "current_sleeve_actions", "research_assessment", "research_dispositions", "mandate_review", "forecasts"}
PROSE_FIELDS = {"executive_summary", "primary_theme", "secondary_theme", "cash_role", "rationale", "reason", "decision",
        "reason_for_departure", "mechanism", "pricing", "portfolio_fit", "portfolio_action", "allocation_effect", "merit_reason",
        "investment_case_summary", "why_better_than_hold", "why_better_than_cash", "downside", "why_preferred",
        "hold_case", "smaller_change_case", "chosen_case", "cost_assumptions", "comparison_summary", "commentary", "observed_expectation", "theme_explanation",
        "assessment", "scope", "structural_horizon", "premise_update", "falsification", "sizing_tradeoff", "what_changes",
        "claim", "implication", "portfolio_consequence", "unanswered_question", "assumptions"}
PROSE_LISTS = {"notes", "contrary_evidence", "portfolio_level_comments", "conditions", "implementation_notes", "risk_flags"}


def claim_patch_paths(document):
    """The checker and applicator share the actual current document's writable paths."""
    from .portfolio_independent import decision_document
    current = decision_document(document)
    if isinstance(document.get("commentary"), dict):
        current["commentary"] = {key: value for key, value in document["commentary"].items()
                                 if key in {"comparison_summary", "portfolio_level_comments", "asset_class_comments"}}
    paths = []
    def visit(value, path):
        if not path or path[0] not in PROSE_ROOTS:
            return
        if isinstance(value, str):
            if path[-1] in PROSE_FIELDS or type(path[-1]) is int and path[-2] in PROSE_LISTS:
                paths.append({"path": path, "expected_hash": digest(value)})
        elif isinstance(value, dict):
            for key, child in value.items():
                visit(child, [*path, key])
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, [*path, index])
    for key, value in current.items():
        visit(value, [key])
    return paths


def apply_claim_patches(proposal, response, evidence=None):
    """Only replace matching text fields; review repairs cannot silently move capital."""
    result, applied, rejected = deepcopy(proposal), [], []
    known = {row["id"] for row in (evidence or {}).get("facts", [])}
    writable = {tuple(row["path"]) for row in claim_patch_paths(proposal)}
    for patch in response.get("patches") or []:
        if not isinstance(patch, dict):
            rejected.append({"patch": patch, "rejection_reason": "invalid_patch"})
            continue
        path = patch.get("path")
        if not isinstance(path, list) or not path or not isinstance(path[0], str) or path[0] not in PROSE_ROOTS:
            rejected.append({**patch, "rejection_reason": "unknown_path"})
            continue
        if not patch.get("reason") or (evidence is not None and any(ref not in known for ref in patch.get("fact_ids") or [])):
            rejected.append({**patch, "rejection_reason": "invalid_reference" if patch.get("reason") else "missing_reason"})
            continue
        try:
            parent = result
            for key in path[:-1]:
                parent = parent[key]
            before, after = parent[path[-1]], patch.get("replacement")
            if not isinstance(before, str) or not isinstance(after, str):
                raise ValueError("numeric_or_structural_change")
            if before == after:
                rejected.append({**patch, "rejection_reason": "already_applied", "status": "superseded"})
                continue
            if before != patch.get("original") or patch.get("expected_hash", digest(before)) != digest(before):
                raise ValueError("stale_original")
            if tuple(path) not in writable:
                raise ValueError("unsupported_field")
            parent[path[-1]] = after
            applied.append(patch)
        except (KeyError, IndexError, TypeError):
            rejected.append({**patch, "rejection_reason": "unknown_path"})
        except ValueError as exc:
            rejected.append({**patch, "rejection_reason": str(exc)})
    # A text correction is itself a review of the existing case, not a reason to regenerate it.
    for patch in applied:
        path = patch["path"]
        if path[0] == "asset_class_targets" and len(path) > 2 and type(path[1]) is int and evidence is not None:
            row = result["asset_class_targets"][path[1]]
            if row.get("detail_status") == "current" and substantive_details(row):
                row["detail_evidence_hash"] = detail_basis(row, evidence)
    result["claim_corrections"] = [*result.get("claim_corrections", []), *applied]
    result["unapplied_claim_corrections"] = [*result.get("unapplied_claim_corrections", []), *rejected]
    return result
