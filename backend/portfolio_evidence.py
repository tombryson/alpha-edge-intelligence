"""Source-linked, point-in-time evidence for the portfolio workflow."""

from __future__ import annotations

import math
import re
import json
from datetime import datetime, timezone
from typing import Any

from .portfolio_runtime import business_data, digest
from .portfolio_sources import RESEARCH_PROVIDERS


def timestamp(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def research_packet(lanes: list[dict], cutoff: str) -> dict:
    sources, research = {}, []
    for lane in lanes:
        for provider in RESEARCH_PROVIDERS:
            result = lane.get(provider) or {}
            summary = result.get("research_summary") or result.get("summary") or ""
            if summary:
                research.append({"lane": lane.get("label"), "provider": provider, "text": summary,
                                 "model": result.get("model") or (result.get("provider_metadata") or {}).get("model")})
            for row in result.get("results") or []:
                url = str(row.get("url") or "")
                if not url:
                    continue
                source_id = "src_" + digest({"url": url, "content": row.get("content", "")})[:16]
                published = row.get("published_at") or None
                sources[source_id] = {"id": source_id, "url": url, "title": row.get("title", ""),
                                      "excerpt": row.get("content", ""), "published_at": published,
                                      "retrieved_at": result.get("performed_at") or cutoff, "provider": provider,
                                      "date_status": "known" if published else "unknown"}
                if row.get("text_provider") == "parallel_citation_excerpt":
                    sources[source_id].update(text_provenance="parallel_citation_excerpt",
                                             date_provenance=row.get("date_provenance", "unknown"))
                for field in ("original_excerpt", "document_context", "context_coverage", "context_limitation"):
                    if row.get(field):
                        sources[source_id][field] = ({key: value for key, value in row[field].items() if key != "sections"}
                                                     if field == "document_context" else row[field])
    return {"as_of": cutoff, "sources": list(sources.values()), "research": research}


FACT_SCHEMA = [{"id": "unique fact id", "kind": "observed_macro | market_price | implied_expectation | forecast", "metric": "specific metric", "value": "number or string", "unit": "unit",
                "benchmark": "specific instrument, series or GDP model", "currency": "currency or not_applicable",
                "observed_at": "ISO date", "published_at": "ISO date/time", "vintage": "release version",
                "source_ids": ["source id from source_packet"], "source_excerpt": "exact supporting source text",
                "measurement": {"reference_period": "period measured or null", "annualization": "quarterly SAAR, Q4/Q4, year-on-year or null",
                    "horizon_months": "forecast/pricing horizon or null", "price_basis": "nominal, real or not_applicable",
                    "curve": "issuer/currency yield curve identity when relevant, otherwise null",
                    "inflation_index": "CPI, PCE, core PCE or null"},
                "interpretation": "separate inference, not part of the observed value"}]

FACT_FIELDS = ("kind", "metric", "value", "unit", "benchmark", "currency", "observed_at", "published_at", "vintage")
TYPED_REVIEW_FIELDS = ("observation_type", "reference_period", "target_period", "available_at",
    *("measurement." + field for field in ("reference_period", "annualization", "horizon_months", "price_basis",
        "curve", "inflation_index", "issuer", "maturity_months", "quote_convention")),
    *("applicability." + field for field in ("subject", "geography", "instrument")),
    *("locator." + field for field in ("page", "row", "column")))
FACT_SCHEMA[0].update(
    observation_type="quote | period_statistic | forecast | qualitative | derived",
    reference_period="actual measured period, not an invented observation day",
    target_period="forecast target period or null",
    available_at="source release timestamp with offset when known; never assume a timezone",
    applicability={"subject": "economic exposure", "geography": "source geography or unknown",
                   "instrument": "instrument or operating stage", "comparison_group": "shared economic question, retaining different scopes"},
    locator={"page": "page number or null", "row": "table row or null", "column": "complete column header hierarchy or null"})
FACT_SCHEMA[0]["measurement"].update(issuer="issuer for yield comparisons or null",
    maturity_months="instrument maturity, not investor horizon or duration; null when unknown")
FACT_CHECK_SCHEMA = [{"fact_id": "exact fact identifier", "checks": {
    key: "supported | unsupported | unresolved | not_applicable; assess typed fields when present in this fact" for key in (*FACT_FIELDS, *TYPED_REVIEW_FIELDS)},
    "reason": "Explain whether the cited source supports this exact observation, not merely a matching number"}]
FACT_CHECK_SCHEMA[0]["correction"] = {
    "changes": {key: "corrected value; omit fields that do not change" for key in (*FACT_FIELDS, "observation_type", "measurement", "applicability", "locator", "reference_period", "target_period", "available_at", "source_excerpt")},
    "checks": {key: "supported | unsupported | unresolved | not_applicable for the corrected observation" for key in (*FACT_FIELDS, *TYPED_REVIEW_FIELDS)},
    "reason": "exact source location and correction, or null"}


def observation_type(fact):
    explicit = fact.get("observation_type")
    if explicit in {"quote", "period_statistic", "forecast", "qualitative", "derived"}:
        return explicit
    return {"forecast": "forecast", "market_price": "quote", "observed_macro": "period_statistic"}.get(fact.get("kind"), "quote")


def fact_field(fact, path):
    value = fact
    for part in path.split("."):
        value = value.get(part) if isinstance(value, dict) else None
    return value


def review_fields(fact):
    return (*FACT_FIELDS, *(key for key in TYPED_REVIEW_FIELDS if fact_field(fact, key) not in (None, "", {}, [])))


def observation_fields(fact):
    fields = {"kind", "metric", "value", "benchmark", "unit", "currency"}
    if observation_type(fact) == "quote":
        fields.add("observed_at")
    elif observation_type(fact) == "period_statistic" and not (
            fact.get("reference_period") or (fact.get("measurement") or {}).get("reference_period")):
        fields.add("observed_at")  # Compatibility with older date-only statistics.
    if observation_type(fact) == "qualitative":
        fields -= {"unit", "currency"}
    if fact.get("observation_type") == "forecast" and not (
            fact.get("reference_period") or (fact.get("measurement") or {}).get("horizon_months")):
        fields.add("target_period")
    fields.update(key for key in review_fields(fact) if key in TYPED_REVIEW_FIELDS)
    return fields


def availability(value, cutoff):
    """A date has day precision; a local clock without an offset is not UTC."""
    if not value:
        return "unknown"
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return "unknown"
    now = timestamp(cutoff)
    if not now:
        return "unknown"
    if len(str(value)) == 10:
        return "after_cutoff" if parsed.date() > now.date() else "available" if parsed.date() < now.date() else "same_day_unknown"
    if parsed.tzinfo is None:
        return "timezone_unknown"
    return "after_cutoff" if parsed > now else "available"


def material_fact_issues(fact):
    metadata = {"Missing published_at", "Invalid published_at", "Missing vintage", "Publication timezone unknown"}
    return [issue for issue in fact.get("verification_issues", []) if issue not in metadata]


def field_supported(fields, key):
    return fields.get(key) == "supported" or fields.get(key) == "not_applicable" and key in {"currency", "vintage", "observed_at", "unit"}


def observation_supported(fact, checks):
    return all(field_supported(checks, key) or (
        checks.get(key) == "not_applicable" and fact_field(fact, key) == "not_applicable"
    ) for key in observation_fields(fact))


def fact_fingerprint(fact: dict) -> str:
    fields = {key: fact.get(key) for key in (*FACT_FIELDS, "source_ids", "source_excerpt", "source_digest")}
    for key in ("measurement", "observation_type", "reference_period", "target_period", "available_at", "applicability", "locator"):
        if fact.get(key):
            fields[key] = fact[key]
    return digest(fields)


def observation_identity(fact: dict) -> str:
    """Observation identity must not depend on a retrieved document's mutable metadata."""
    fields = {key: fact.get(key) for key in (*FACT_FIELDS, "measurement")}
    fields.update({key: fact[key] for key in ("reference_period", "target_period", "applicability") if fact.get(key) is not None})
    return digest(fields)


def fact_is_supported(fact: dict) -> bool:
    review = fact.get("claim_review") or {}
    return (fact.get("evidence_status") == "source_matched" and fact.get("claim_status") == "supported"
            and review.get("fact_hash") == fact_fingerprint(fact)
            and not fact.get("superseded_by") and not fact.get("supersession_conflicts")
            and all(review.get("checks", {}).get(key) == "supported" for key in review_fields(fact)))


def fact_observation_is_supported(fact: dict) -> bool:
    """Unknown publication metadata does not negate a checked, dated observation."""
    review = fact.get("claim_review") or {}
    checks = review.get("checks") or {}
    return (review.get("fact_hash") == fact_fingerprint(fact) and bool(review.get("reason"))
            and bool(fact.get("source_ids")) and bool(fact.get("source_excerpt"))
            and not fact.get("superseded_by") and not fact.get("supersession_conflicts")
            and observation_supported(fact, checks)
            and not any(checks.get(key) == "unsupported" for key in ("published_at", "vintage"))
            and not material_fact_issues(fact))


def reusable_fact_checks(facts: list[dict], packet: dict, *, contract=None, compatible_contracts=()) -> tuple[list[dict], list[dict]]:
    """Reuse verdicts only against the exact observation and current source content."""
    facts = [row for row in facts if isinstance(row, dict)]
    normalized = normalize_facts(facts, packet)
    checks, pending = [], []
    for previous, current in zip(facts, normalized):
        review = previous.get("claim_review") or {}
        fields = review.get("checks") or {}
        if (review.get("fact_hash") == fact_fingerprint(current) and review.get("reason")
                and (contract is None or review.get("check_contract") in {None, contract, *compatible_contracts})
                and all(fields.get(key) in {"supported", "unsupported", "unresolved", "not_applicable"} for key in review_fields(current))):
            checks.append({"fact_id": current["id"], "checks": fields, "reason": review["reason"],
                           "review_issues": review.get("issues", []),
                           "check_contract": review.get("check_contract"), "check_model": review.get("check_model"),
                           "contract_status": "versioned" if review.get("check_contract") else "legacy_unversioned"})
        else:
            pending.append(current)
    return checks, pending


def apply_fact_checks(facts: list[dict], checks: list[dict], packet: dict) -> list[dict]:
    reviewed = normalize_facts(facts, packet)
    by_id = {row.get("fact_id"): row for row in checks if isinstance(row, dict)}
    for fact in reviewed:
        check = by_id.get(fact["id"], {})
        fields = check.get("checks") or {}
        if check.get("reason") and all(fields.get(key) == "supported" for key in ("value", "unit", "metric")):
            numeric_warning = "Claimed numeric value is not in the supporting excerpt; a derivation must be reviewed"
            if numeric_warning in fact.get("verification_issues", []):
                fact["verification_issues"].remove(numeric_warning)
                fact["value_derivation"] = {"operation": "source_reviewed_conversion", "reason": check["reason"]}
        status = "unsupported" if any(fields.get(key) == "unsupported" for key in observation_fields(fact)) else "unresolved"
        if not material_fact_issues(fact) and check.get("reason") and observation_supported(fact, fields):
            status = "supported"
        fact["claim_status"] = status
        if not material_fact_issues(fact):
            fact["evidence_status"] = "source_matched"
        fact["claim_review"] = {"fact_hash": fact_fingerprint(fact), "checks": fields,
                                "reason": check.get("reason") or "Source support has not been assessed",
                                "issues": check.get("review_issues") or [],
                                "check_contract": check.get("check_contract"), "check_model": check.get("check_model"),
                                "contract_status": "versioned" if check.get("check_contract") else "legacy_unversioned"}
        fact["review_dimensions"] = {name: (
            "unsupported" if any(fields.get(key) == "unsupported" for key in keys) else
            "supported" if all(fields.get(key) in {"supported", "not_applicable"} for key in keys) else "unresolved")
            for name, keys in {"observation": ("kind", "metric", "value", "benchmark"),
                               "units_and_currency": ("unit", "currency"), "observation_date": ("observed_at",),
                               "publication_metadata": ("published_at", "vintage"),
                               "typed_observation": tuple(key for key in review_fields(fact) if key in TYPED_REVIEW_FIELDS)}.items() if keys}
    corrections = []
    for fact in reviewed:
        correction = by_id.get(fact["id"], {}).get("correction") or {}
        changes = correction.get("changes")
        allowed = {*FACT_FIELDS, "measurement", "reference_period", "target_period", "source_excerpt", "locator", "observation_type", "available_at", "applicability"}
        if not isinstance(changes, dict) or not changes or set(changes) - allowed or not correction.get("reason"):
            continue
        changes = {key: value for key, value in changes.items() if fact.get(key) != value}
        if not changes:
            continue
        candidate = {**fact, **changes}
        candidate.pop("superseded_by", None)
        candidate.pop("supersedes", None)
        candidate["id"] = "fact_" + observation_identity(candidate)[:20]
        if candidate["id"] == fact["id"]:
            continue
        checked = apply_fact_checks([candidate], [{"fact_id": candidate["id"], "checks": correction.get("checks", {}),
            "check_contract": by_id.get(fact["id"], {}).get("check_contract"),
            "check_model": by_id.get(fact["id"], {}).get("check_model"),
            "reason": correction["reason"]}], packet)[0]
        if fact_observation_is_supported(checked):
            checked.update(supersedes=fact["id"], correction_reason=correction["reason"])
            fact["superseded_by"] = checked["id"]
            corrections.append(checked)
        else:
            fact["proposed_correction"] = {"changes": changes, "reason": correction["reason"], "status": "unverified"}
    return reviewed + corrections


def source_text(value) -> str:
    """Compare rendered source text without altering quantities, signs or raw provenance."""
    from html import unescape
    text = unescape(str(value or ""))
    text = re.sub(r"</?(?:p|div|span|br|strong|em|b|i|table|thead|tbody|tr|th|td)\b[^>]*>", " ", text, flags=re.I)
    text = re.sub(r"\\([\\`*_{}\[\]()#+\-.!|>])", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\(https?://[^)]+\)", r"\1", text)
    text = re.sub(r"(\*\*|__|`)(.+?)\1", r"\2", text)
    return " ".join(text.replace("|", " ").split())


def numeric_source_derivation(fact: dict, excerpt: str) -> dict | None:
    """Recognise a signed change, not an arbitrary sign flip or unit conversion."""
    value = fact.get("value")
    excerpt = source_text(excerpt)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        return None
    metric = str(fact.get("metric") or "").casefold()
    if not re.search(r"\b(change|draw|draws|withdrawal|decline|decrease|increase|growth)\b", metric):
        return None
    number_pattern = r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?"
    for match in re.finditer(number_pattern, excerpt):
        magnitude = float(match[0].replace(",", ""))
        if magnitude < 0 or magnitude != abs(value):
            continue
        # Only the clause immediately attached to this number can establish its direction.
        before = re.split(r"[.;!?]|,\s+(?:while|but|whereas)", excerpt[:match.start()])[-1].casefold()
        before = re.split(number_pattern, before)[-1]
        before = re.split(r"\b(?:while|whereas|but)\b", before)[-1]
        negative = re.search(r"\b(?:fell|fallen|declined|decreased|dropped|plunged|drew|draws?|withdrawals?)\b", before)
        positive = re.search(r"\b(?:rose|risen|increased|grew|gained|builds?)\b", before)
        # 'Fell to 95' is a level; 'rose by 95 from 100' is a change.
        level = re.search(r"\b(?:at|to|from)\s*(?:about|around|approximately)?\s*$", before)
        cumulative_draw = re.search(r"\bcumulative\s+(?:draws?|withdrawals?)\b[^.!?]*\bto\s*$", before)
        if level and not cumulative_draw:
            continue
        if (negative and not positive and value < 0) or (positive and not negative and value > 0):
            return {"operation": "signed_change", "quoted_magnitude": magnitude,
                    "direction": "decrease" if value < 0 else "increase", "source_excerpt": excerpt}
    return None


def normalize_facts(facts: list, packet: dict) -> list[dict]:
    sources = {row["id"]: row for row in packet.get("sources", [])}
    normalized = []
    for fact in facts:
        if not isinstance(fact, dict):
            continue
        row = business_data(fact)
        row.pop("claim_review", None)
        row["claim_status"] = "unresolved"
        row["id"] = str(row.get("id") or "fact_" + digest(row)[:16])
        issues = []
        for key in observation_fields(row):
            if fact_field(row, key) in (None, ""):
                issues.append(f"Missing {key}")
        if isinstance(row.get("value"), (int, float)) and (isinstance(row["value"], bool) or not math.isfinite(row["value"])):
            issues.append("Non-finite or boolean numeric value")
        references = row.get("source_ids") or []
        if not isinstance(references, list) or any(not isinstance(ref, str) for ref in references):
            references = []
            issues.append("Source references must be identifiers")
        row["source_digest"] = digest([sources.get(ref) for ref in references])
        excerpt = source_text(row.get("source_excerpt"))
        if excerpt != " ".join(str(row.get("source_excerpt") or "").split()) or any(
                source_text(sources.get(ref, {}).get("excerpt")) != " ".join(str(sources.get(ref, {}).get("excerpt") or "").split())
                for ref in references):
            row["source_text_normalization"] = {"method": "rendered-text-v1", "supporting_excerpt": excerpt,
                                                 "raw_source_preserved": True}
        if not references or any(ref not in sources for ref in references):
            issues.append("Source reference unavailable")
        if not excerpt or not any(excerpt in source_text(sources.get(ref, {}).get("excerpt")) for ref in references):
            issues.append("Supporting excerpt not found in retrieved source")
        if isinstance(row.get("value"), (int, float)) and not isinstance(row["value"], bool):
            quoted_numbers = [float(value.replace(",", "")) for value in re.findall(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?", excerpt)]
            row.pop("value_derivation", None)
            if row["value"] not in quoted_numbers:
                derivation = numeric_source_derivation(row, excerpt)
                if derivation:
                    row["value_derivation"] = derivation
                else:
                    issues.append("Claimed numeric value is not in the supporting excerpt; a derivation must be reviewed")
        for reference in references:
            if availability(sources.get(reference, {}).get("published_at"), packet.get("as_of")) == "after_cutoff":
                issues.append("Referenced source was published after the research cutoff")
        row["availability_status"] = availability(row.get("available_at") or row.get("published_at"), packet.get("as_of"))
        if row.get("available_at") and row["availability_status"] == "after_cutoff":
            issues.append("available_at is after the research cutoff")
        for field in ("observed_at", "published_at"):
            if field == "observed_at" and field not in observation_fields(row):
                continue
            date = timestamp(row.get(field))
            if date is None:
                issues.append(f"Invalid {field}")
            elif availability(row.get(field), packet.get("as_of")) == "after_cutoff":
                issues.append(f"{field} is after the research cutoff")
        row["evidence_status"] = "source_matched" if not issues else "needs_verification"
        row["verification_issues"] = issues
        normalized.append(row)
    return normalized


def merge_briefs(briefs: list[dict]) -> dict:
    briefs = [business_data(brief) for brief in briefs]
    observations, occupied, aliases = {}, {}, {}
    ambiguous_aliases = set()
    for brief in briefs:
        identifiers = {}
        for row in brief.get("facts", []):
            if not isinstance(row, dict) or not row.get("id"):
                continue
            original = row["id"]
            identity = observation_identity(row)
            stable = observations.get(identity)
            if stable is None:
                historical = bool(re.fullmatch(r"fact_[0-9a-f]{16,64}", original))
                unchanged = row.get("observation_hash", identity) == identity
                stable = original if historical and unchanged and original not in occupied else "fact_" + identity[:20]
                observations[identity], occupied[stable] = stable, identity
            identifiers[original] = stable
            if original in aliases and aliases[original] != stable:
                ambiguous_aliases.add(original)
            aliases[original] = stable
            row["observation_hash"] = identity
        def relink(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key == "fact_ids" and isinstance(item, list):
                        value[key] = [identifiers.get(ref, ref) for ref in item]
                    elif key in {"supersedes", "superseded_by"} and isinstance(item, str):
                        value[key] = identifiers.get(item, item)
                    else:
                        relink(item)
            elif isinstance(value, list):
                for item in value:
                    relink(item)
        relink(brief)
        for fact in brief.get("facts", []):
            if fact.get("id") in identifiers:
                fact["id"] = identifiers[fact["id"]]
    merged: dict = {"executive_summary": "Evidence reconciliation is incomplete. All research lanes are retained for review.",
                   "evidence_status": "incomplete", "lane_assessments": [], "macro_scorecard": {},
                   "market_view": {}, "quadrant_assessment": {"best_fit": "UNASSESSED", "secondary_fit": "NONE"}}
    merged["fact_aliases"] = {key: value for key, value in aliases.items() if key != value and key not in ambiguous_aliases}
    for brief in briefs:
        for key, value in (brief.get("fact_aliases") or {}).items():
            if key not in ambiguous_aliases:
                merged["fact_aliases"][key] = aliases.get(value, value)
    review_candidates, correction_edges = {}, set()
    for brief in briefs:
        for fact in brief.get("facts", []):
            review_candidates.setdefault(fact["id"], []).append(fact)
            for old, new in ((fact.get("supersedes"), fact["id"]), (fact["id"], fact.get("superseded_by"))):
                if isinstance(old, str) and isinstance(new, str) and old != new:
                    correction_edges.add((merged["fact_aliases"].get(old, old), merged["fact_aliases"].get(new, new)))
            for new in fact.get("supersession_conflicts", []):
                correction_edges.add((fact["id"], merged["fact_aliases"].get(new, new)))
            for old in fact.get("supersedes_ids", []):
                correction_edges.add((merged["fact_aliases"].get(old, old), fact["id"]))
    for field in ("facts", "commodity_prices", "broker_themes", "asset_class_implications", "asset_class_coverage", "watchpoints", "source_shortlist", "research_questions"):
        rows = {}
        for brief in briefs:
            for row in brief.get(field) or []:
                key = row.get("id") if field in {"facts", "research_questions"} and isinstance(row, dict) else digest(row)
                copied = business_data(row)
                if field == "facts":
                    previous = rows.get(key, {})
                    for relation in ("research_question_ids", "comparison_groups"):
                        copied[relation] = list(dict.fromkeys([*previous.get(relation, []), *copied.get(relation, [])]))
                    variants = [*previous.get("source_variants", [])]
                    for observation in (previous, copied):
                        if observation.get("source_ids"):
                            variant = {field: observation.get(field) for field in ("source_ids", "source_excerpt", "source_digest")}
                            if variant not in variants:
                                variants.append(variant)
                    copied["source_variants"] = variants
                    copied["source_ids"] = list(dict.fromkeys([*previous.get("source_ids", []), *copied.get("source_ids", [])]))
                    previous_review = rows.get(key, {}).get("claim_review") or {}
                    if previous_review.get("fact_hash") == fact_fingerprint(copied) and not copied.get("claim_review"):
                        copied["claim_review"] = previous_review
                        copied["claim_status"] = rows[key].get("claim_status", "unresolved")
                    interpretations = [*(rows.get(key, {}).get("interpretations") or []), *(row.get("interpretations") or []), row.get("interpretation")]
                    copied["interpretations"] = list(dict.fromkeys(text for text in interpretations if isinstance(text, str) and text.strip()))
                rows[key] = copied
        merged[field] = list(rows.values())
    source_rows, research_rows = {}, {}
    for brief in briefs:
        packet = brief.get("source_packet") or {}
        merged.setdefault("as_of", packet.get("as_of"))
        for row in packet.get("sources", []):
            source_rows[row["id"]] = row
        for row in packet.get("research", []):
            research_rows[digest(row)] = row
        merged["lane_assessments"].append({key: business_data(brief.get(key)) for key in
                                          ("evidence_lane", "executive_summary", "macro_scorecard", "market_view", "quadrant_assessment", "evidence_status")})
    merged["source_packet"] = {"as_of": merged.get("as_of"), "sources": list(source_rows.values()), "research": list(research_rows.values())}
    # Raw extraction is not a newer review. Revalidate receipts against the final
    # source snapshot, and restore correction edges independently of merge order.
    for index, row in enumerate(merged["facts"]):
        candidates = [candidate for candidate in review_candidates.get(row["id"], []) if candidate.get("claim_review")]
        normalized = normalize_facts([row], merged["source_packet"])[0] if candidates else row
        matching = [candidate for candidate in candidates
                    if (candidate.get("claim_review") or {}).get("fact_hash") == fact_fingerprint(normalized)]
        if matching:
            # Keep adverse checks when equally current reviewers disagree.
            checks = {}
            rank = {"supported": 0, "not_applicable": 0, "unresolved": 1, "unsupported": 2}
            for candidate in matching:
                for field, verdict in candidate["claim_review"].get("checks", {}).items():
                    if field not in checks or rank.get(verdict, 1) > rank.get(checks[field], 1):
                        checks[field] = verdict
            reasons = list(dict.fromkeys(candidate["claim_review"].get("reason", "") for candidate in matching))
            contracts = {candidate["claim_review"].get("check_contract") for candidate in matching}
            models = {candidate["claim_review"].get("check_model") for candidate in matching}
            normalized = apply_fact_checks([normalized], [{"fact_id": row["id"], "checks": checks,
                "check_contract": next(iter(contracts)) if len(contracts) == 1 else "mixed:" + digest(sorted(c or "legacy" for c in contracts)),
                "check_model": next(iter(models)) if len(models) == 1 else "mixed",
                "reason": "; ".join(filter(None, reasons))}], merged["source_packet"])[0]
        successors = sorted(new for old, new in correction_edges if old == row["id"])
        predecessors = sorted(old for old, new in correction_edges if new == row["id"])
        for field in ("superseded_by", "supersedes", "supersession_conflicts"):
            normalized.pop(field, None)
        if len(successors) == 1:
            normalized["superseded_by"] = successors[0]
        elif successors:
            normalized["supersession_conflicts"] = successors
            normalized["claim_status"] = "unresolved"
        if len(predecessors) == 1:
            normalized["supersedes"] = predecessors[0]
        elif predecessors:
            normalized["supersedes_ids"] = predecessors
        merged["facts"][index] = normalized
    merged["source_count"] = len(source_rows)
    merged["evidence_ensemble"] = {"mode": "unreconciled", "lane_count": len(briefs), "enabled": len(briefs) > 1,
                                   "agreement_summary": "Reconciliation incomplete; no consensus inferred.", "major_disagreements": [],
                                   "material_minority_themes": [], "missing_or_weak_coverage": []}
    return merged


def coverage_quality(rows: list[dict]) -> dict:
    assessed = [row for row in rows if row.get("evidence_strength") in {"LOW", "MEDIUM", "HIGH"}
                and (row.get("fact_ids") or row.get("source_ids")) and row.get("evidence_summary")]
    return {"status": "ok" if assessed else "unassessed", "row_count": len(rows), "non_none_row_count": len(assessed)}


def validate_stage(value: dict, prompt: dict) -> list[str]:
    errors = []
    try:
        json.dumps(value, allow_nan=False)
    except ValueError:
        errors.append("Non-finite numbers are not valid evidence or allocations")
    schema = prompt.get("required_schema") or {}
    def nested_shape(template, item, path):
        if isinstance(template, dict):
            if not isinstance(item, dict):
                errors.append(f"{path} must be an object")
                return
            for key in template.keys() & item.keys():
                nested_shape(template[key], item[key], f"{path}.{key}")
        elif isinstance(template, list):
            if not isinstance(item, list):
                errors.append(f"{path} must be an array")
            elif template:
                for index, child in enumerate(item):
                    nested_shape(template[0], child, f"{path}[{index}]")
        elif isinstance(item, (list, dict)):
            errors.append(f"{path} must be a scalar value")
    nested_shape(schema, value, "response")
    if "allocation_details" in schema:
        rows = value.get("allocation_details")
        expected = [row["asset_class"] for row in prompt.get("assigned_allocations", [])]
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            errors.append("Investment details must be objects")
        else:
            identifiers = [row.get("asset_class") for row in rows]
            if sorted(map(str, identifiers)) != sorted(expected):
                errors.append("Return each assigned asset exactly once, without adding or changing allocations")
            fields = set(schema["allocation_details"][0])
            for row in rows:
                if set(row) != fields:
                    errors.append("Investment details require all requested fields and must not change weights or actions")
    if "fact_checks" in schema:
        checks = value.get("fact_checks")
        supplied_facts = {row["id"]: row for row in (prompt.get("evidence") or {}).get("facts", [])}
        expected = set(supplied_facts)
        if not isinstance(checks, list) or any(not isinstance(row, dict) for row in checks):
            errors.append("Fact checks must be objects")
        else:
            identifiers = [row.get("fact_id") for row in checks]
            if len(identifiers) != len(set(str(item) for item in identifiers)) or set(str(item) for item in identifiers) != expected:
                errors.append("Review every supplied fact exactly once")
            for row in checks:
                fields = row.get("checks")
                if not isinstance(fields, dict):
                    errors.append(f"fact_checks[{row.get('fact_id')}].checks: expected field-level review verdicts")
                else:
                    for key in review_fields(supplied_facts.get(row.get("fact_id"), {})):
                        if not isinstance(fields.get(key), str) or fields[key] not in {"supported", "unsupported", "unresolved", "not_applicable"}:
                            errors.append(f"fact_checks[{row.get('fact_id')}].checks.{key}: missing or invalid verdict; use supported, unsupported or unresolved")
                if not isinstance(row.get("reason"), str) or not row["reason"].strip():
                    errors.append(f"fact_checks[{row.get('fact_id')}].reason: missing source-review explanation")
    for key in schema:
        if key not in value:
            errors.append(f"Missing required field {key}")
        elif isinstance(schema[key], list) and not isinstance(value[key], list):
            errors.append(f"{key} must be an array")
        elif isinstance(schema[key], dict) and not isinstance(value[key], dict):
            errors.append(f"{key} must be an object")
        elif isinstance(schema[key], list) and schema[key] and isinstance(schema[key][0], dict) and isinstance(value[key], list):
            if any(not isinstance(row, dict) for row in value[key]):
                errors.append(f"{key} entries must be objects")
    if "asset_class_targets" in schema:
        rows = value.get("asset_class_targets")
        if not isinstance(rows, list) or not rows:
            errors.append("No allocation proposal returned")
        elif any(not isinstance(row, dict) for row in rows):
            errors.append("Allocation rows must be objects")
        else:
            total = 0.0
            seen = set()
            for row in rows:
                asset = str(row.get("asset_class") or "").upper().replace("_", "").replace("-", "")
                if not asset or asset in seen:
                    errors.append("Missing or duplicate asset class")
                seen.add(asset)
                for field in ("fact_ids", "contrary_evidence", "alternatives"):
                    if field in row and not isinstance(row[field], list):
                        errors.append(f"{asset}: {field} must be an array")
                for field in ("implementation", "market_pricing", "investment_case"):
                    if field in row and not isinstance(row[field], dict):
                        errors.append(f"{asset}: {field} must be an object")
                if isinstance(row.get("fact_ids"), list) and any(not isinstance(ref, str) for ref in row["fact_ids"]):
                    errors.append(f"{asset}: fact identifiers must be strings")
                numbers = [row.get(k) for k in ("min_pct", "target_pct", "max_pct")]
                if any(isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) for n in numbers):
                    errors.append(f"{asset}: finite numeric ranges required")
                    continue
                lo, target, hi = numbers
                if not 0 <= lo <= target <= hi <= 100:
                    errors.append(f"{asset}: invalid allocation range")
                total += target
            if abs(total - 100) > 0.05:
                errors.append(f"Point allocation totals {total:.2f}%, not 100%; explicitly fund all sleeves and cash")
            context = prompt.get("portfolio_context") or {}
            if context.get("current_asset_classes") and not errors:
                from .portfolio_decisions import funding_ledger
                snapshot = {"portfolio": context.get("portfolio") or {}, "mandate": context.get("mandate") or {},
                    "asset_classes": [{**row, "portfolio_pct": row.get("current_pct")} for row in context["current_asset_classes"]]}
                errors.extend(funding_ledger(snapshot, value)["issues"])
    return errors
