"""Stage-specific portfolio inputs; the canonical evidence and decisions stay outside prompts."""

from copy import deepcopy

from .portfolio_decisions import asset_key
from .portfolio_tasks import allocation_context, evidence_for_decisions, investment_evidence


def observation_brief(evidence, decisions=None):
    """Lossless observation view with identical source passages stored only once."""
    packet = investment_evidence(evidence) if decisions is None else evidence_for_decisions(evidence, decisions)
    columns = ["id", "kind", "metric", "value", "unit", "benchmark", "currency", "observed_at", "published_at",
               "vintage", "measurement", "source_ids", "source_review", "verification_issues", "value_derivation", "passage_id"]
    passages, rows = {}, []
    for fact in packet.get("facts", []):
        row = deepcopy(fact)
        excerpt = row.pop("source_excerpt", None)
        if excerpt:
            from .portfolio_runtime import digest
            identifier = "passage_" + digest(excerpt)[:20]
            passages[identifier] = excerpt
            row["passage_id"] = identifier
        # Preserve future observation fields as well as today's schema.
        for field in row:
            if field not in columns:
                columns.append(field)
        rows.append(row)
    return {"evidence_view": "observation-index-v1", "as_of": packet.get("as_of"),
        "observations": {"columns": columns, "rows": [[row.get(field) for field in columns] for row in rows]},
        "source_passages": passages,
        "fact_aliases": deepcopy(packet.get("fact_aliases", {})),
        "research_questions": deepcopy(packet.get("research_questions", [])), "sources": deepcopy(packet.get("sources", [])),
        "research_limitations": deepcopy(packet.get("research_limitations", [])),
        "premise_changes": deepcopy(packet.get("premise_changes", [])),
        "market_context_status": packet.get("market_context_status"),
        "evidence_scope": deepcopy(packet.get("evidence_scope", {})),
        "source_access": "Each observation's passage_id resolves to its exact excerpt in source_passages. Identical excerpts are stored once; facts, measurement distinctions and source-review results remain separate. Missing passages are not source confirmation."}


def decision_rows(proposal, assets=None):
    keys = None if assets is None else {asset_key(name) for name in assets}
    return [deepcopy(row) for row in proposal.get("asset_class_targets", [])
            if keys is None or asset_key(row.get("asset_class")) in keys]


def expand_observations(packet):
    """Restore the canonical request view for code that selects facts by identity."""
    index = packet["observations"]
    facts = []
    for values in index["rows"]:
        row = dict(zip(index["columns"], deepcopy(values)))
        passage = row.pop("passage_id", None)
        if passage:
            row["source_excerpt"] = packet["source_passages"][passage]
        facts.append(row)
    return {**{key: deepcopy(value) for key, value in packet.items()
               if key not in {"observations", "source_passages", "source_access"}},
            "evidence_view": "investment-v1", "facts": facts}


def scoped_decision(proposal, assets):
    """Affected decisions plus the complete weight table, never archived draft references."""
    keys = {asset_key(name) for name in assets}
    result = {"asset_class_targets": decision_rows(proposal, assets), "portfolio_weights": allocation_context(proposal)}
    for field in ("current_sleeve_actions", "reconciliation"):
        result[field] = [deepcopy(row) for row in proposal.get(field, []) if asset_key(row.get("asset_class")) in keys]
    result["play_assessments"] = [deepcopy(row) for row in proposal.get("play_assessments", [])
        if keys & {asset_key(name) for name in row.get("selected_exposures", [])}]
    return result


def reader_decision(proposal):
    """Financial conclusions for prose, without disposition tables or previous drafts."""
    fields = ("executive_summary", "strategic_view", "asset_class_targets", "play_assessments",
              "excluded_opportunities", "implementation_notes", "implementation_choice", "monitoring_triggers", "risk_flags", "scenario_risks")
    from .portfolio_independent import decision_document
    document = decision_document(proposal)
    return {field: document[field] for field in fields if field in document}


def review_findings(reviews, proposal=None):
    dispositions = {row.get("finding_id"): row for row in (proposal or {}).get("review_dispositions", [])}
    return [{"council_lane": review.get("council_lane"), "stage_status": review.get("stage_status"),
             **{field: deepcopy(review[field]) for field in ("review_completion", "review_coverage") if field in review},
             **({"incomplete_review_parts": [{"review_completion": part.get("review_completion") or "failed",
                "review_coverage": deepcopy(part.get("review_coverage"))} for part in review["review_parts"]
                if part.get("review_completion") in {"partial", "failed"} or part.get("stage_status") != "complete"]}
                if review.get("review_parts") else {}),
             "scenario_risks": deepcopy(review.get("scenario_risks", [])),
             "findings": [deepcopy(row) for row in review.get("findings", []) if proposal is None or
                dispositions.get(row.get("id"), {}).get("status") not in {"accepted", "rebutted"}
                or not dispositions.get(row.get("id"), {}).get("reason")],
             "warnings": deepcopy(review.get("warnings", []))} for review in reviews]


def settlement_inputs(evidence, provisional, details, reviews):
    """Source detail for the cases being settled, not a replay of every researched theme."""
    from .portfolio_judgment import detail_basis
    from .portfolio_tasks import investment_details
    previous = {asset_key(row.get("asset_class")): row for row in provisional.get("asset_class_targets", [])}
    changed = []
    for row in investment_details(details or {}).get("asset_class_targets", []):
        old = previous.get(asset_key(row.get("asset_class")), {})
        if row.get("detail_evidence_hash") and row.get("detail_evidence_hash") == old.get("detail_evidence_hash"):
            if old.get("detail_evidence_hash") == detail_basis(old, evidence):
                continue
        changed.append(row)
    cases = [previous[asset_key(row["asset_class"])] for row in changed if asset_key(row.get("asset_class")) in previous]
    findings = review_findings(reviews, provisional)
    evidence_packet = observation_brief(evidence, [cases, changed, findings])
    return {"investment_details": {"asset_class_targets": changed}, "reviews": findings,
        "evidence_brief": evidence_packet,
        "settlement_scope": {"changed_case_ids": [row["asset_class"] for row in changed],
            "pending_finding_ids": [row.get("id") for review in findings for row in review["findings"]],
            "rule": "All weights and the saved decision remain visible. Source detail is scoped to the changed investment cases and unresolved findings; unchanged research is not newly reviewed."}}


def evidence_for_revision(evidence, proposal, scope, review):
    assets = [*scope.get("asset_classes", []), *scope.get("funding_asset_classes", [])]
    return evidence_for_decisions(evidence, [scoped_decision(proposal, assets)["asset_class_targets"],
        scoped_decision(proposal, assets)["current_sleeve_actions"], review.get("decision_revisions", []),
        {"asset_classes": assets}])


def pending_update(proposal):
    record = proposal.get("final_reconciliation") or {}
    candidate = record.get("unapplied_candidate") or {}
    response = record.get("response") or {}
    assets = [row.get("asset_class") for row in response.get("target_updates", []) if isinstance(row, dict)]
    assets += response.get("removed_target_ids") or []
    return {"issues": deepcopy(record.get("issues", [])),
        "candidate": scoped_decision(candidate, [asset for asset in assets if asset]) if candidate else {}}


def payload_accounting(prompt):
    """Accounting describes each actual dispatch; it does not enforce a size ceiling."""
    import json
    def size(value):
        return len(json.dumps(value, ensure_ascii=False).encode())
    packets = {}
    for name, packet in prompt.items():
        if not isinstance(packet, dict):
            continue
        index = packet.get("observations") or {}
        fact_ids = [row.get("id") for row in packet.get("facts", []) if isinstance(row, dict)]
        if "id" in index.get("columns", []):
            position = index["columns"].index("id")
            fact_ids += [row[position] for row in index.get("rows", [])]
        if fact_ids or packet.get("evidence_scope"):
            packets[name] = {"fact_ids": fact_ids, "source_ids": [row.get("id") for row in packet.get("sources", [])],
                "question_ids": [row.get("question_id") or row.get("id") for row in packet.get("research_questions", [])],
                "scope": deepcopy(packet.get("evidence_scope", {}))}
    return {"contract": "dispatch-payload-v1", "bytes": size(prompt),
        "fields": {key: size(value) for key, value in prompt.items()}, "evidence_packets": packets,
        "review_scope": deepcopy(prompt.get("review_scope", {})), "decision_scope": deepcopy(prompt.get("scope", {}))}
