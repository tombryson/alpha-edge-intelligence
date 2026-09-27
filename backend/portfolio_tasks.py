"""Bound portfolio requests without discarding evidence or changing allocations."""

from copy import deepcopy

from .portfolio_runtime import CURRENT_RUNTIME, business_data
from .portfolio_exposures import decision_relationships as _decision_relationships


def _present(value):
    if isinstance(value, dict):
        return {key: _present(item) for key, item in value.items() if item not in (None, "", [], {})}
    if isinstance(value, list):
        return [_present(item) for item in value]
    return value


def investment_evidence(brief: dict) -> dict:
    """Lossless observation values; no repeated model interpretations or audit receipts."""
    # A request view is not a raw ledger. Reprojecting it used to erase provenance.
    if brief.get("evidence_view") == "observation-index-v1":
        from .portfolio_requests import expand_observations
        return expand_observations(brief)
    if brief.get("evidence_view") == "investment-v1" or (
            "sources" in brief and "initial_market_context" in brief and "source_packet" not in brief):
        return deepcopy(brief)
    from .portfolio_research import research_readthrough, refresh_signed_evidence
    brief = refresh_signed_evidence(brief, detached=False)
    fields = ("id", "kind", "metric", "value", "unit", "benchmark", "currency", "observed_at", "published_at",
              "vintage", "measurement", "source_ids", "source_excerpt", "verification_issues",
              "observation_type", "reference_period", "target_period", "available_at", "availability_status",
              "applicability", "locator", "research_question_ids", "comparison_groups", "supersedes", "superseded_by",
              "supersedes_ids", "supersession_conflicts", "correction_reason")
    facts = []
    for fact in brief.get("facts", []):
        row = {field: fact[field] for field in fields if field in fact}
        row["source_review"] = {"status": fact.get("claim_status", "unresolved"),
            "reason": (fact.get("claim_review") or {}).get("reason"),
            "dimensions": fact.get("review_dimensions", {}),
            "issues": (fact.get("claim_review") or {}).get("issues", []),
            "adverse_checks": {key: value for key, value in (fact.get("claim_review") or {}).get("checks", {}).items()
                               if value == "unsupported"}}
        if fact.get("value_derivation"):
            row["value_derivation"] = {key: value for key, value in fact["value_derivation"].items() if key != "source_excerpt"}
        facts.append(_present(row))
    result = {"evidence_view": "investment-v1",
        "as_of": brief.get("as_of") or (brief.get("source_packet") or {}).get("as_of"),
        "fact_aliases": deepcopy(brief.get("fact_aliases") or {}),
        "research_questions": research_readthrough(brief), "facts": facts,
        "sources": [{key: source.get(key) for key in ("id", "url", "title", "published_at")}
                    for source in (brief.get("source_packet") or {}).get("sources", [])],
        "initial_market_context": {key: business_data(brief[key]) for key in (
            "market_view", "macro_scorecard", "quadrant_assessment", "material_minority_themes") if brief.get(key)},
        "premise_changes": deepcopy(brief.get("premise_changes", [])),
        "market_context_status": brief.get("market_context_status", "initial_unreconciled"),
        "research_limitations": brief.get("research_limitations", []),
        "evidence_scope": {"available_facts": len(facts), "included_facts": len(facts),
            "note": "Full observations and source excerpts retained. Earlier market context predates focused research; reconcile it against the question answers and contrary observations. Audit metadata and repeated interpretations remain in the saved ledger."}}
    if brief.get("market_context_status") == "requires_reconciliation":
        result.pop("initial_market_context", None)
    return _present(result)

INVESTMENT_DETAIL_SCHEMA = {
    "implementation": {"instrument_type": "specific instrument type", "currency": "currency", "risk_attributes": {
        "duration_years": "number, not_applicable or null", "credit_quality": "string, not_applicable or null", "currency_hedging": "string or null",
        "operating_stage": "producer/developer/clinical/cash-generative/not_applicable or null"}},
    "market_pricing": {"benchmark": "specific priced instrument or expectation", "observed_expectation": "what the market price implies, or unknown", "fact_ids": ["source-matched pricing fact id"]},
    "investment_case": {"why_better_than_hold": "comparison or unknown", "why_better_than_cash": "comparison or unknown", "downside": "contrary scenario or unknown", "cost_assumptions": "assumptions or unknown", "horizon_months": "number or null"},
    "alternatives": [{"name": "holding, cash or an alternative implementation", "why_preferred": "evidence-based comparison", "fact_ids": ["fact id"]}],
}
INVESTMENT_DETAIL_SCHEMA["investment_case"].update(
    causal_chain=[{"link": "economic change -> beneficiary -> margins/cash flow -> valuation -> return/risk -> size",
                  "assessment": "decision-relevant conclusion", "basis": "observed | assumption | unresolved", "fact_ids": ["supporting or contrary fact ID"]}],
    scope="geography, operating stage and instrument; distinguish source scope from investor scope",
    structural_horizon="structural holding-period thesis, separately from shorter catalyst timing",
    premise_update="what new or corrected evidence changes; why the indicated weight remains justified or needs reconsideration",
    falsification="observable change that would invalidate the case",
    sizing_tradeoff="marginal benefit, common-factor risk and opportunity cost versus holding/cash/another expression")


def evidence_for_analysis(brief: dict) -> dict:
    """Keep the fact ledger and dissent; raw documents live in the saved artifact."""
    runtime = CURRENT_RUNTIME.get()
    if (runtime is not None and runtime.workflow_version >= 4) or (runtime is None and "research_questions" in brief):
        return investment_evidence(brief)
    result = business_data(brief)
    packet = result.pop("source_packet", {})
    result["sources"] = [{key: source.get(key) for key in
                          ("id", "url", "title", "published_at", "retrieved_at")}
                         for source in packet.get("sources", result.get("sources", []))]
    if runtime is not None and runtime.workflow_version == 1:
        return result
    for fact in result.get("facts", []):
        fact.pop("source_digest", None)
        fact.pop("source_variants", None)
        fact.pop("observation_hash", None)
        review = fact.get("claim_review") or {}
        if review:
            # Retain every adverse/unknown verdict; full review receipts stay in the artifact.
            fact["claim_review"] = {"reason": review.get("reason"), "issues": review.get("issues", []),
                "checks": {key: value for key, value in review.get("checks", {}).items() if value != "supported"}}
        if "interpretation" in fact or "interpretations" in fact:
            fact["interpretations"] = list(dict.fromkeys(text for text in
                [fact.pop("interpretation", None), *fact.get("interpretations", [])] if text))
    return result


def evidence_for_decisions(brief: dict, decisions, *, question_ids=None) -> dict:
    """Select cases and opposing observations through declared evidence relationships."""
    from .portfolio_decisions import asset_key
    from .portfolio_judgment import linked_facts
    from .portfolio_research import research_readthrough
    if brief.get("evidence_view") == "observation-index-v1":
        from .portfolio_requests import expand_observations
        brief = expand_observations(brief)
    relationships = _decision_relationships(decisions)
    questions = (brief.get("research_questions", []) if brief.get("evidence_view") == "investment-v1"
                 else research_readthrough(brief))
    selected = []
    for row in questions:
        identifier = row.get("question_id") or row.get("id")
        if question_ids is not None:
            matches = bool({identifier, *row.get("related_question_ids", [])} & set(question_ids))
        else:
            matches = (bool({identifier, *row.get("related_question_ids", [])} & relationships["questions"]) or
                bool({asset_key(name) for name in row.get("asset_classes", [])} & relationships["assets"]) or
                bool(set(row.get("component_ids", [])) & relationships["components"]) or
                (bool(set(row.get("play_ids", [])) & relationships["plays"]) and not relationships["components"]))
        if matches:
            selected.append(row)
    relevant = linked_facts(decisions) | linked_facts(selected)
    plan = decision_source_check_plan(brief, {"fact_ids": sorted(relevant)})
    relevant = set(plan["fact_ids"])
    all_facts = brief.get("facts", [])
    facts = [fact for fact in all_facts if fact.get("id") in relevant]
    source_ids = {ref for fact in facts for ref in fact.get("source_ids", [])}
    packet = brief.get("source_packet") or {}
    # Select before projecting: no full-archive copy followed by throwing most away.
    scoped = {**brief, "facts": facts, "research_questions": []}
    if "source_packet" in brief:
        scoped["source_packet"] = {**packet, "sources": [row for row in packet.get("sources", []) if row.get("id") in source_ids]}
    result = evidence_for_analysis(scoped)
    result.setdefault("facts", [])
    result["research_questions"] = selected
    # Global narrative links must not silently turn a scoped case back into the entire ledger.
    result.pop("initial_market_context", None)
    result.pop("other_observations", None)
    result["evidence_scope"] = {"included_facts": len(result["facts"]),
        "available_facts": (brief.get("evidence_scope") or {}).get("available_facts", len(all_facts)),
        "question_ids": [row.get("question_id") or row.get("id") for row in selected],
        "missing_fact_ids": plan["missing_fact_ids"],
        "note": "Decision citations, current linked answers, same-scope comparators and explicit corrections. Discovery topics do not imply decision dependencies; the full archive remains available."}
    source_ids = {ref for fact in result["facts"] for ref in fact.get("source_ids", [])}
    result["sources"] = [source for source in result.get("sources", []) if source.get("id") in source_ids]
    return result


def evidence_for_review(brief, decisions, question_ids=None, *, full_catalogue=True):
    """Case evidence plus relevant discovery entries; portfolio review sees the whole index."""
    result = evidence_for_decisions(brief, decisions, question_ids=question_ids)
    # Retrieved-in-the-same-search is not the same as used in this answer.
    # Keep answer support and its comparators in full; the remaining observations
    # stay discoverable by ID, rather than multiplying every case's source text.
    all_facts = brief.get("facts", [])
    relevant = {row["id"] for row in result.get("facts", [])}
    questions = {row["question_id"] for row in result.get("research_questions", [])}
    columns = ["id", "metric", "benchmark", "observed_at"]
    result["other_observations"] = {"columns": columns, "rows": [[row.get(key) for key in columns]
        for row in all_facts if row["id"] not in relevant and
        (full_catalogue or questions.intersection(row.get("research_question_ids", [])))]}
    result["other_observations"]["scope"] = "whole_archive" if full_catalogue else "assigned_questions"
    result["evidence_scope"]["included_facts"] = len(result["facts"])
    result["evidence_scope"]["note"] = "Decision citations, related research answers, same-scope comparable observations and explicit corrections are shown in full. Other observations are discovery entries only, not substantiated investment conclusions. Raise an explicit fact-ID evidence request to inspect them."
    source_ids = {ref for row in result["facts"] for ref in row.get("source_ids", [])}
    result["sources"] = [row for row in result.get("sources", []) if row["id"] in source_ids]
    return result


def allocation_context(proposal):
    """Whole-book funding context without repeated investment essays or audit receipts."""
    return [{key: deepcopy(row[key]) for key in ("asset_class", "display_name", "target_pct", "purpose") if key in row}
            for row in proposal.get("asset_class_targets", [])]


def investment_details(proposal):
    from .portfolio_judgment import detail_basis
    fields = ("asset_class", *INVESTMENT_DETAIL_SCHEMA, "detail_status", "detail_evidence_hash")
    return {"asset_class_targets": [{**{key: deepcopy(row[key]) for key in fields if key in row},
                                    "detail_decision_hash": row.get("detail_decision_hash") or detail_basis(row)}
                                  for row in proposal.get("asset_class_targets", [])],
            "warnings": deepcopy(proposal.get("warnings", []))}


def compact_decision_checks(checks):
    """Keep the calculations and unresolved issues, not a second copy of their input essays."""
    result = business_data(checks)
    comparison = result.get("implementation_comparison") or {}
    comparison.pop("smaller_change_proposal", None)
    comparison.pop("choice", None)
    for view in ("destination", "smaller_change"):
        funding = (comparison.get(view) or {}).get("funding") or {}
        if "rows" in funding:
            funding["rows"] = [{key: row.get(key) for key in ("asset_class", "current_pct", "target_pct", "trade_pct", "status")}
                               for row in funding["rows"]]
    return result


def source_batches(packet: dict, *, max_chars: int = 18000) -> list[dict]:
    """Cover every source character, with overlap across long-document boundaries."""
    if max_chars <= 200:
        raise ValueError("Source batch size must exceed the 200-character overlap")
    batches, sources, size = [], [], 0
    for source in packet.get("sources", []):
        excerpt = str(source.get("excerpt") or "")
        step = max_chars - 200
        for offset in range(0, max(len(excerpt), 1), step):
            part = {**source, "excerpt": excerpt[offset:offset + max_chars], "excerpt_offset": offset}
            cost = len(part["excerpt"])
            if sources and (size + cost > max_chars or len(sources) >= 4):
                batches.append({"as_of": packet.get("as_of"), "sources": sources, "research": []})
                sources, size = [], 0
            sources.append(part)
            size += cost
    if sources:
        batches.append({"as_of": packet.get("as_of"), "sources": sources, "research": []})
    return batches


def fact_review_batches(facts: list[dict], packet: dict) -> list[dict]:
    """Keep related claims together and bound request size without clipping evidence."""
    import json
    sources = {source["id"]: source for source in packet.get("sources", [])}
    groups = {}
    for fact in facts:
        groups.setdefault(tuple(sorted(set(fact.get("source_ids") or []))), []).append(fact)

    def batch(rows):
        refs = dict.fromkeys(ref for row in rows for ref in (row.get("source_ids") or []))
        return {"facts": rows, "source_packet": {"as_of": packet.get("as_of"),
            "sources": [sources[ref] for ref in refs if ref in sources]}}

    batches, rows = [], []
    for group in groups.values():
        for fact in group:
            candidate = batch([*rows, fact])
            # These are packing targets, not truncation or model output limits.
            # Allow one full source once, so a long document does not force one
            # request per claim. Additional sources/claims use the packing target.
            source_bytes = [len(json.dumps(source).encode()) for source in candidate["source_packet"]["sources"]]
            target_bytes = 32000 + max(source_bytes, default=0)
            if rows and (len(rows) >= 16 or len(json.dumps(candidate).encode()) > target_bytes):
                batches.append(batch(rows))
                rows = []
            rows.append(fact)
    if rows:
        batches.append(batch(rows))
    return batches


def decision_source_check_plan(evidence: dict, proposal: dict, reviews=()) -> dict:
    """Check live decision dependencies and factual challenges, not every archived argument."""
    from .portfolio_decisions import asset_key
    from .portfolio_judgment import linked_facts
    # Supplementary ideas do not commission checks. Adopted investment cases still do.
    proposal = {**proposal, "play_assessments": [row for row in proposal.get("play_assessments") or []
                                               if isinstance(row, dict) and row.get("assessment_mode") != "brief"]}
    aliases = evidence.get("fact_aliases") or {}
    def canonical(refs):
        return {aliases.get(ref, ref) for ref in refs}
    selected = canonical(linked_facts(proposal))
    decision_refs = set(selected)
    reasons = {ref: {"decision_or_alternative"} for ref in selected}
    assets = _decision_relationships({key: proposal.get(key) for key in
        ("asset_class_targets", "current_sleeve_actions", "smaller_change_alternative", "play_assessments", "excluded_opportunities")})["assets"]
    dispositions = {row.get("finding_id") for row in proposal.get("review_dispositions", [])
                    if isinstance(row, dict) and row.get("status") == "unresolved"}
    findings = []
    for review in reviews:
        for finding in review.get("findings", []):
            refs = canonical(linked_facts(finding))
            challenged = canonical(set(finding.get("challenged_fact_ids", []))) if "challenged_fact_ids" in finding else refs
            affects_case = bool(challenged & decision_refs) or (
                finding.get("material_to_decision") is True and asset_key(finding.get("asset_class")) in assets)
            # Missing research and general disagreement remain in the review, not as
            # new obligations to certify every observation cited during the debate.
            if finding.get("id") in dispositions or affects_case and finding.get("kind") == "factual_correction":
                findings.append(finding.get("id"))
                for ref in refs:
                    reasons.setdefault(ref, set()).add("factual_challenge:" + str(finding.get("id")))
                selected.update(refs)
    facts = evidence.get("facts", [])
    def period(fact):
        return fact.get("target_period") or fact.get("reference_period") or (fact.get("measurement") or {}).get("reference_period") or fact.get("observed_at")
    def series(fact):
        from .portfolio_runtime import digest
        clean = lambda value: " ".join(str(value or "").casefold().split())
        key = tuple(clean(fact.get(k)) for k in ("metric", "benchmark", "unit")) + (clean(period(fact)),)
        if not all(key):
            return None
        scope = {key: value for key, value in (fact.get("applicability") or {}).items()
                 if key != "comparison_group" and value not in (None, "")}
        measurement = {key: value for key, value in (fact.get("measurement") or {}).items() if value not in (None, "")}
        return (*key, clean(fact.get("kind")), clean(fact.get("observation_type")), clean(fact.get("currency")),
                clean(fact.get("reference_period")), digest(scope), digest(measurement))
    # A shared topic is not a shared measurement. Preserve genuine conflicting
    # observations, but require matching scope; unknown scope is not a wildcard.
    series_keys = {series(f) for f in facts if f["id"] in selected} - {None}
    for fact in facts:
        if series(fact) in series_keys:
            selected.add(fact["id"])
            reasons.setdefault(fact["id"], set()).add("same_measurement_or_opposing_case")
    while True:
        extra = {f["id"] for f in facts if f.get("supersedes") in selected or
                 set(f.get("supersedes_ids") or []) & selected}
        if extra <= selected:
            break
        for ref in extra - selected:
            reasons.setdefault(ref, set()).add("corrected_observation")
        selected.update(extra)
    known = {f["id"] for f in facts}
    return {"contract": "decision-source-check-v2", "fact_ids": sorted(selected & known),
            "missing_fact_ids": sorted(selected - known), "finding_ids": sorted(f for f in findings if f),
            "archive_fact_count": len(facts), "selected_fact_count": len(selected & known),
            "selection_reasons": {ref: sorted(reasons[ref]) for ref in sorted(selected)},
            "unselected_status": "Archived evidence remains available; not checked in this decision pass"}


def allocation_batches(rows: list[dict]) -> list[list[dict]]:
    return [rows[offset:offset + 4] for offset in range(0, len(rows), 4)]


async def cached_source_extraction(runtime, batch, model, contract, extract, parser):
    """Reuse identical source chunks across lanes, not interpretations or financial judgments."""
    import asyncio
    from contextlib import AsyncExitStack
    import json
    from .portfolio_runtime import digest
    from .portfolio_evidence import source_text
    cache = runtime.partial.setdefault("source_extractions", {})
    if not hasattr(runtime, "source_extraction_locks"):
        runtime.source_extraction_locks = {}
    keys = {digest({"model": model, "contract": contract, "cutoff": batch.get("as_of"),
        "source": {key: source.get(key) for key in ("id", "url", "excerpt", "excerpt_offset", "published_at")}}): source
        for source in batch.get("sources", [])}
    async with AsyncExitStack() as stack:
        for key in sorted(keys):
            await stack.enter_async_context(runtime.source_extraction_locks.setdefault(key, asyncio.Lock()))
        retained = [deepcopy(fact) for key in keys for fact in cache.get(key, {}).get("facts", [])]
        missing = {key: source for key, source in keys.items() if key not in cache}
        if not missing:
            progress_key = runtime.progress.register(digest(sorted(keys)), "extraction", "Reusing saved source observations", model)
            runtime.progress.update(progress_key, status="complete", reused=True)
            runtime._report_progress()
            return {"content": json.dumps({"facts": retained}), "stage_status": "complete", "source_cache_reused": len(keys)}
        response = await extract(list(missing.values()))
        parsed = parser(response.get("content") or "") or {}
        facts = parsed.get("facts") or []
        if response.get("stage_status") == "complete":
            for key, source in missing.items():
                relevant = [row for row in facts if source["id"] in row.get("source_ids", [])]
                if any(row.get("source_ids") != [source["id"]] or not source_text(row.get("source_excerpt"))
                       or source_text(row["source_excerpt"]) not in source_text(source.get("excerpt")) for row in relevant):
                    continue
                cache[key] = {"source_id": source["id"], "facts": deepcopy(relevant)}
            await runtime.asave_request("extraction:" + digest(sorted(missing)),
                partial_records={"source_extractions": {key: cache[key] for key in missing if key in cache}})
        return {**response, "content": json.dumps({"facts": [*retained, *facts]}), "source_cache_reused": len(keys) - len(missing)}
