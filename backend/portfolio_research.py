"""Decision-specific research contracts, independent of providers and asset taxonomies."""

from copy import deepcopy
import re

from .portfolio_runtime import digest


CONTRACT = "question-led-research-v4"
MEASUREMENT_FIELDS = ("subject", "measure", "geography", "period", "basis", "unit", "instrument", "vintage")
QUESTION_SCHEMA = {
    "reuse_question_id": "existing research question id for the same question and observation scope, otherwise null",
    "question": "one concise factual research question; not a request to predict prices or allocate",
    "search_queries": ["2-3 complementary keyword queries, 3-6 words each, naming the economic subject; no portfolio JSON"],
    "deep_research_reason": "empty for ordinary discovery; only explain a difficult multi-source investigation needed if Search and document inspection leave a decisive premise unresolved",
    "topic": "canonical economic subject, shared across related questions",
    "economic_question": "canonical question key; reuse a supplied key for the same economic question",
    "observation_scope": {"subject": "canonical commodity, sector or instrument", "measure": "observable economic measure",
        "geography": "canonical region", "period": "observation period", "horizon": "decision horizon",
        "basis": "spot/forecast, frequency, unit and instrument distinctions relevant to identity"},
    "dimension_aliases": [{"dimension": "new wording of a required dimension", "existing_dimension": "exact same dimension in reuse_question_id; never merge different measures"}],
    "dimension_measurements": [{"dimension": "exact required dimension",
        "scope": {field: "explicit canonical value; preserve distinctions, use not_applicable only when genuinely inapplicable"
                  for field in MEASUREMENT_FIELDS},
        "reuse_measurement_id": "existing exact measurement id, otherwise null"}],
    "geography": "market or region", "period": "observation period", "horizon": "decision horizon",
    "required_dimensions": ["specific observable input or forecast assumption needed to answer"],
    "asset_classes": ["affected economic exposures; new exposures permitted"],
    "play_ids": ["affected play id, only when plays supplied"], "component_ids": ["affected component id"],
    "component_names": ["exact component names from play_components when IDs have not yet been assigned"],
    "material_reason": "which economic conclusion could change and why",
    "decision_consequence": "specific direction, size, instrument, funding or portfolio-risk choice this answer could change; empty if none",
    "reuse_assessment": "what existing facts establish and exactly what is still missing",
    "existing_fact_ids": ["existing facts considered"],
    "inspect_source_ids": ["existing source IDs whose original report can resolve a material missing dimension before buying another search; otherwise empty"],
    "decision_impact": "high | medium | low", "critical_premise": "boolean: is the central thesis unassessable without this?",
    "status": "answered | unanswered | not_market",
    "answers": [{"dimension": "exact required dimension", "status": "answered | partial | conflicting | unresolved",
                 "answer": "what the sources establish, including limitations", "fact_ids": ["supporting fact id"]}],
}
ANSWER_SCHEMA = QUESTION_SCHEMA["answers"]
COMPONENT_SCHEMA = {"play_id": "exact submitted play id",
    "coverage_status": "complete | incomplete | unassessed; compare the entire original idea with the inventory, not just the recognised components",
    "coverage_reason": "explicit completeness assessment accounting for every named exposure and relative preference in the original text",
    "unresolved_source_text": ["exact passages whose economic components remain unaccounted for; empty only after the full idea was checked"],
    "components": [{
    "economic_key": "distinct exposure and direction; not the entire basket",
    "name": "human readable economic component", "source_text": "exact excerpt of the submitted idea",
    "direction": "long | avoid | relative_preference | other; do not invent a short",
    "expression": "economic exposure or comparison", "purpose": "return | hedge | liquidity | other"}]}


def key(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


PHASE_ORDER = {"independent": 0, "current": 1, "plays": 2, "challenge": 3}


def restore_phase_research(baseline, saved, phase):
    """Admit saved sources at their original information boundary, including old checkpoints."""
    from .portfolio_evidence import merge_briefs
    boundary = PHASE_ORDER[phase]
    reports = list((saved.get("research_phase_results") or {}).values()) + (saved.get("research_phases") or [])
    origins, appearances = {}, {}
    for report in reports:
        for question in report.get("questions", []):
            if report.get("phase") in PHASE_ORDER:
                appearances.setdefault(question.get("id"), set()).add(report["phase"])
                if question.get("retrieval_status") in {"succeeded", "failed"}:
                    origins.setdefault(question.get("id"), set()).add(report["phase"])
    lanes, seen = [], set()
    records = [*(saved.get("targeted_research_results") or {}).items(),
               *((identifier, {**lane, "source_inspection": True}) for identifier, lane in (saved.get("document_inspections") or {}).items()),
               *((lane.get("label", ""), lane) for lane in saved.get("research_lane_archive", []))]
    for storage_key, lane in records:
        if not isinstance(lane, dict):
            continue
        origin = lane.get("phase") or storage_key.split(":", 1)[0]
        if origin not in PHASE_ORDER:
            # Old keys could be overwritten by later phases: choose the latest possible origin.
            identifier = (lane.get("question") or {}).get("id")
            origin = max(origins.get(identifier) or appearances.get(identifier) or {"challenge"}, key=PHASE_ORDER.get)
        lane = deepcopy(lane)
        lane["phase"] = origin
        question = lane.get("question") or {}
        if question.get("id"):
            for fact in (lane.get("evidence_brief") or {}).get("facts", []):
                fact["research_question_ids"] = list(dict.fromkeys([*fact.get("research_question_ids", []), question["id"]]))
                fact["comparison_groups"] = list(dict.fromkeys([*fact.get("comparison_groups", []), question.get("economic_question") or question["id"]]))
        if PHASE_ORDER[origin] <= boundary and (lane.get("evidence_brief") or {}).get("facts"):
            fingerprint = digest(lane)
            if fingerprint not in seen:
                lanes.append(lane)
                seen.add(fingerprint)
    result = deepcopy(baseline)
    if lanes:
        merged = merge_briefs([baseline, *(lane["evidence_brief"] for lane in lanes)])
        result.update({field: merged[field] for field in
            ("facts", "fact_aliases", "source_packet", "source_count", "lane_assessments")})
    result = refresh_signed_evidence(result)
    registry = {row["id"]: merge_question(None, row, result) for row in result.get("research_questions", [])}
    for report in reports:
        if PHASE_ORDER.get(report.get("phase"), 99) <= boundary:
            for row in report.get("questions", []):
                registry[row["id"]] = merge_question(registry.get(row["id"]), row, result)
    for lane in lanes:
        row = deepcopy(lane.get("question") or {})
        if not row.get("id"):
            continue
        row["answers"] = [*row.get("answers", []), *lane["evidence_brief"].get("question_answers", [])]
        if not lane.get("source_inspection") and row.get("retrieval_status") == "succeeded" and row.get("processing_status") == "complete":
            row["searched_dimensions"] = list(dict.fromkeys([*row.get("searched_dimensions", []), *row.get("required_dimensions", [])]))
        registry[row["id"]] = merge_question(registry.get(row["id"]), row, result)
    result["research_questions"] = list(registry.values())
    result["unresolved_market_questions"] = [{"id": row["id"], "question": row["question"],
        "asset_classes": row.get("asset_classes", []), "play_ids": row.get("play_ids", []),
        "reason": "Material research dimensions remain unresolved"} for row in registry.values() if row["status"] != "answered"]
    result["research_reuse"] = {"phase": phase, "lanes": len(lanes),
        "restored_fact_ids": sorted({fact["id"] for lane in lanes for fact in lane["evidence_brief"]["facts"]})}
    return result, lanes


def matching_question(row, registry):
    """Reuse explicit or exact identities; never guess that two financial concepts are equivalent."""
    if row["id"] in registry:
        return registry[row["id"]]
    candidates = [old for old in registry.values() if all(key(old.get(field)) == key(row.get(field))
        for field in ("geography", "period", "horizon")) and (
        (key(old.get("topic")) == key(row.get("topic")) and key(old.get("question")) == key(row.get("question")))
        or (row.get("economic_question") and key(row["economic_question"]) == key(old.get("economic_question")))
        or (observation_scope(row) is not None and observation_scope(row) == observation_scope(old))
        or row.get("reuse_question_id") == old["id"])
        and not (observation_scope(row) and observation_scope(old) and observation_scope(row) != observation_scope(old))]
    return candidates[0] if len(candidates) == 1 else None


def observation_scope(row):
    value = row.get("observation_scope") or {}
    fields = ("subject", "measure", "geography", "period", "horizon", "basis")
    return {field: key(value[field]) for field in fields} if all(isinstance(value.get(field), str) and value[field].strip() for field in fields) else None


def measurement_bindings(question):
    """Identity is per observation, independent of the portfolio's investment horizon."""
    dimensions = {key(value) for value in question.get("required_dimensions", [])}
    result, ambiguous = {}, set()
    for binding in question.get("dimension_measurements", []) or []:
        if not isinstance(binding, dict) or key(binding.get("dimension")) not in dimensions:
            continue
        scope = binding.get("scope") or {}
        if not all(isinstance(scope.get(field), str) and scope[field].strip() for field in MEASUREMENT_FIELDS):
            continue
        canonical = {field: " ".join(scope[field].casefold().split()) for field in MEASUREMENT_FIELDS}
        identifier = "measurement_" + digest(canonical)[:20]
        # A supplied reuse ID cannot override a changed region, period or basis.
        if binding.get("reuse_measurement_id") not in (None, "", identifier):
            continue
        dimension = key(binding["dimension"])
        if dimension in result and result[dimension]["id"] != identifier:
            ambiguous.add(dimension)
        result[dimension] = {"id": identifier, "scope": canonical, "dimension": binding["dimension"]}
    return {dimension: row for dimension, row in result.items() if dimension not in ambiguous}


def measurement_registry(evidence):
    registry = {}
    for question in evidence.get("research_questions", []):
        checked = coverage(question, evidence, question.get("answers"))
        searched = {key(value) for value in question.get("searched_dimensions", [])}
        for dimension, binding in measurement_bindings(question).items():
            record = registry.setdefault(binding["id"], {"id": binding["id"], "scope": binding["scope"],
                "answers": [], "searched": False, "question_ids": []})
            record["question_ids"].append(question["id"])
            record["searched"] |= dimension in searched
            for answer in checked["answers"]:
                if key(answer["dimension"]) == dimension and answer not in record["answers"]:
                    record["answers"].append(deepcopy(answer))
    return registry


def reuse_measurements(question, evidence):
    result = deepcopy(question)
    registry = measurement_registry(evidence)
    reused = []
    for dimension, binding in measurement_bindings(question).items():
        saved = registry.get(binding["id"])
        if not saved:
            continue
        reused.append(binding["id"])
        for answer in saved["answers"]:
            result.setdefault("answers", []).append({**deepcopy(answer), "dimension": binding["dimension"],
                "measurement_id": binding["id"]})
        if saved["searched"]:
            result.setdefault("searched_dimensions", []).append(binding["dimension"])
    result["searched_dimensions"] = list(dict.fromkeys(result.get("searched_dimensions", [])))
    result["reused_measurement_ids"] = reused
    result.update(coverage(result, evidence, result.get("answers")))
    return result


def deduplicate_measurement_searches(questions):
    """Dispatch a shared dimension once; consumers receive its answer after the wave."""
    owned, result = {}, []
    for question in questions:
        if question.get("inspect_source_ids") or question.get("resume_attempt"):
            result.append(question)
            continue
        bindings = measurement_bindings(question)
        dimensions = []
        for dimension in question.get("required_dimensions", []):
            binding = bindings.get(key(dimension))
            if binding and binding["id"] in owned:
                continue
            if binding:
                owned[binding["id"]] = question["id"]
            dimensions.append(dimension)
        if dimensions:
            narrowed = deepcopy(question)
            narrowed["required_dimensions"] = dimensions
            if dimensions != question["required_dimensions"]:
                narrowed["question"] = f"{question.get('topic') or 'Market evidence'}: establish " + "; ".join(dimensions) + "."
            result.append(narrowed)
    return result


def saved_source_lane(question, saved, phase):
    """Resume extraction from already purchased sources, even when structuring failed."""
    required = {key(value) for value in question.get("required_dimensions", [])}
    for lane in (saved.get("targeted_research_results") or {}).values():
        if lane.get("source_inspection"):
            continue
        original = lane.get("question") or {}
        if (PHASE_ORDER.get(lane.get("phase"), 99) <= PHASE_ORDER[phase]
                and original.get("id") == question.get("id")
                and " ".join(str(lane.get("query") or original.get("question", "")).split())
                    == " ".join(question.get("question", "").split())
                and required <= {key(value) for value in original.get("required_dimensions", [])}
                and any(row.get("content") for row in (lane.get("parallel") or {}).get("results", []))):
            return lane
    return None


def pending_source_attempt(question, saved, phase):
    """Resume an unfinished exact attempt, not a renamed or expanded paid request."""
    missing = {key(value) for value in question.get("missing_dimensions", [])}
    for lane in reversed(list((saved.get("targeted_research_results") or {}).values())):
        original = lane.get("question") or {}
        result = lane.get("parallel") or {}
        if (lane.get("source_inspection") or original.get("id") != question.get("id")
                or PHASE_ORDER.get(lane.get("phase"), 99) > PHASE_ORDER[phase]
                or not missing.intersection(key(value) for value in original.get("required_dimensions", []))
                or "retrieval_context" not in lane):
            continue
        if (result.get("resumable") or (not result and original.get("processing_status") == "pending")
                or (result.get("results") and original.get("processing_status") != "complete")):
            return {**deepcopy(question), "question": lane["query"],
                "required_dimensions": list(original["required_dimensions"]),
                "retrieval_context": deepcopy(lane["retrieval_context"]),
                "retrieval_options": deepcopy(lane.get("retrieval_options")),
                "resume_attempt": True, "inspect_source_ids": []}
    return None


def pending_inspection_sources(question, evidence, saved, phase):
    """A new source version can answer an old dimension without repeating discovery."""
    sources = {row["id"]: row for row in (evidence.get("source_packet") or {}).get("sources", [])}
    requested = {ref: digest({field: sources[ref].get(field) for field in ("url", "excerpt", "published_at")})
                 for ref in question.get("inspect_source_ids", []) if ref in sources}
    dimensions = {key(value) for value in question.get("missing_dimensions", [])}
    for lane in (saved.get("document_inspections") or {}).values():
        original = lane.get("question") or {}
        if (original.get("id") != question.get("id") or PHASE_ORDER.get(lane.get("phase"), 99) > PHASE_ORDER[phase]
                or lane.get("error") or (lane.get("evidence_brief") or {}).get("stage_error")
                or not dimensions <= {key(value) for value in original.get("required_dimensions", [])}):
            continue
        inspected = lane.get("inspected_source_versions") or {}
        requested = {ref: version for ref, version in requested.items() if inspected.get(ref) != version}
    return requested


def planning_prompt(phase, evidence, neutral, *, holdings=None, plays=None, candidates=None):
    from .portfolio_tasks import investment_evidence
    from .portfolio_requests import observation_brief
    discovery = investment_evidence(evidence)
    for fact in discovery.get("facts", []):
        fact.pop("source_excerpt", None)
    discovery = observation_brief(discovery)
    discovery["evidence_view"] = "discovery-index-v1"
    discovery["source_access"] = "Observation discovery index only. Original quotations are not included in this planning request; do not claim new source verification. Use IDs to reuse available observations or identify material gaps."
    discovery.pop("research_questions", None)
    current_answers = {row["question_id"]: row for row in research_readthrough(evidence)}
    prompt = {
        "task": "Plan decisive market research before investment judgments: " + phase,
        "research_contract": CONTRACT, "research_cutoff": neutral["research_cutoff"],
        "rules": [
            "Return JSON research plans only, not allocations, ratings or an investment opinion. Do not browse in this call.",
            "Research only questions whose plausible answers could change the thesis, exposure, sizing, funding or risk decision. Name that consequence in material_reason; omit interesting but inconsequential questions.",
            "Reuse supplied observations and dimension-specific answers first. This discovery index omits source passages: IDs identify evidence, not proof or new source verification. State exact remaining gaps without guessing.",
            "Use inspect_source_ids only when a discovered primary document could resolve a material gap. Inspect new relevant documents; do not reread unchanged sources or repeat unchanged discovery.",
            "Investigate decisive physical conditions, earnings transmission, offsets and priced expectations, including structural developments and overlooked beneficiaries. No fixed asset catalogue or borrowed fund universe.",
            "Ask for dated quantities, mechanisms and forecast assumptions, not price predictions. Distinguish production, capacity, exports, inventories and net balances; avoid double-counting.",
            "Weight contrary evidence by relevance, magnitude and reliability, not artificial bull/bear balance. Missing evidence is not evidence against an idea.",
            "Resolve paraphrases to research_registry IDs and economic_question first; combine dimensions using explicit dimension_aliases. Preserve distinct instruments, units, regions, bases and periods.",
            "Bind reusable dimensions to the exact measurement_registry scope. One historical observation can serve multiple investment horizons; do not invent equivalences.",
            "Return questions in strict investment-priority order: decision consequence and exposure, the unresolved assumption, then whether research can resolve it. A high label alone is not priority. Include unheld opportunities; no quota per asset. Use short individual questions, no portfolio JSON or checklists.",
            "Supply complementary search_queries for each question. Parallel Search is the first step. Use deep_research_reason only for difficult source reconciliation or multi-step investigations of a high-impact premise, never for a routine quote, missing JSON or a model failure.",
            "Missing mandate, schema fields, source-review flags or wording are not market questions. Mark them not_market. For answered dimensions provide the answer and existing supporting fact IDs.",
        ],
        "required_schema": {"questions": [QUESTION_SCHEMA]},
        "optional_question_metadata": {"decision_dependency": "earnings | valuation | hedge_mechanics | supply_balance | market_quote | other",
            "decision_consequence": "specific sizing, expression or risk choice which this answer could change; omit when unknown"},
        "independent_context": neutral, "evidence_brief": discovery,
        "measurement_registry": list(measurement_registry(evidence).values()),
        "research_registry": [{**{field: deepcopy(row[field]) for field in (
            "id", "question", "topic", "economic_question", "observation_scope", "geography", "period", "horizon",
            "required_dimensions", "searched_dimensions", "missing_dimensions", "status", "asset_classes", "component_ids", "play_ids", "answers", "dimension_measurements") if field in row},
            **{key: value for key, value in current_answers.get(row.get("id"), {}).items()
               if key in {"status", "scope_status", "coverage_note", "related_question_ids", "related_answer_ids"}}}
            for row in evidence.get("research_questions", [])],
    }
    # Planning needs quantities and coverage, not a replay of every source quotation.
    for fact in prompt["evidence_brief"].get("facts", []):
        fact.pop("source_excerpt", None)
    if holdings is not None:
        prompt["current_portfolio"] = holdings
        prompt["rules"].append("No independent ideal or user plays are supplied. Investigate this book on its own merits; do not infer another allocator's weights.")
    if plays is not None:
        prompt["investment_plays"] = plays
        prompt["required_schema"]["play_components"] = [COMPONENT_SCHEMA]
        prompt["rules"].append("Establish each play's distinct components before assessing it. A five-commodity basket has five legs, not five copies of its full sentence. Preserve relative preferences: gold over bonds is not an instruction to short bonds. No rating at this stage. Separately compare the inventory against the ENTIRE original idea and return coverage_status, coverage_reason and unresolved_source_text. A nonempty inventory does not establish completeness.")
    if candidates:
        prompt["candidate_questions"] = candidates
    if phase == "independent":
        prompt["rules"].append("Holdings, their taxonomy and user plays are intentionally absent. Discover your own opportunities from the market research; never substitute another fund's holdings for an unspecified universe.")
    return prompt


def complete_component_plan(plan, plays, evidence):
    """An omitted submitted leg receives a focused question, never an invented score."""
    result = deepcopy(plan)
    components = {component["id"]: (play, component) for play in plays for component in play.get("components", [])}
    questions = result.setdefault("questions", [])
    for question in questions:
        question["component_ids"] = [identifier for identifier in question.get("component_ids", []) if identifier in components]
    assigned = {identifier for question in questions for identifier in question.get("component_ids", [])}
    for identifier, (play, component) in components.items():
        if identifier in assigned:
            continue
        prior = [row for row in evidence.get("research_questions", []) if identifier in row.get("component_ids", [])]
        if prior:
            questions.extend(deepcopy(prior))
            continue
        subject = component.get("expression") or component["name"]
        questions.append({"question": f"What do current primary sources establish about the outlook, economics and priced expectations for {subject}?",
            "topic": subject, "economic_question": "play_component_" + identifier,
            "asset_classes": [subject], "play_ids": [play["id"]], "component_ids": [identifier],
            "required_dimensions": ["causal outlook and offsetting evidence", "cash-flow transmission and priced expectations"],
            "geography": "specified by source; investor scope unknown", "horizon": play.get("horizon") or "investor mandate",
            "material_reason": "This submitted component was omitted from the research plan: " + component.get("source_text", component["name"]),
            "reuse_assessment": "No existing question is explicitly linked to this component; reuse relevant discovered reports first.",
            "existing_fact_ids": [], "decision_impact": "high", "critical_premise": True, "status": "unanswered"})
    result["questions"] = sorted(questions, key=lambda row: not bool(row.get("component_ids")))
    result["component_coverage"] = [{"component_id": identifier, "status": "planned"} for identifier in components]
    return result


def _numeric_disagreement(answers, facts):
    from .portfolio_decisions import number
    values = {}
    for ref in {ref for answer in answers for ref in answer.get("fact_ids", [])
                if ref not in answer.get("qualified_fact_ids", [])}:
        fact = facts.get(ref, {})
        value = number(fact.get("value"))
        period = fact.get("target_period") or fact.get("reference_period") or (fact.get("measurement") or {}).get("reference_period") or fact.get("observed_at")
        if value is None or not period or not all(fact.get(field) for field in ("metric", "benchmark", "unit")):
            continue
        scope = {field: fact.get(field) for field in ("kind", "metric", "benchmark", "unit", "currency", "vintage", "measurement")}
        scope.update(period=period, applicability={field: (fact.get("applicability") or {}).get(field)
            for field in ("subject", "geography", "instrument")})
        values.setdefault(digest(scope), set()).add(value)
    return any(len(group) > 1 for group in values.values())


def coverage(question, brief, answers=None):
    """Validate coverage references, not the truth of a model's economic interpretation."""
    facts = {row.get("id"): row for row in brief.get("facts", [])}
    for alias, canonical in (brief.get("fact_aliases") or {}).items():
        if canonical in facts:
            facts[alias] = facts[canonical]
    sources = {row.get("id") for row in (brief.get("source_packet") or {}).get("sources", [])}
    dimensions = question.get("required_dimensions") or [question["question"]]
    by_dimension = {}
    for row in answers or []:
        if not isinstance(row, dict):
            continue
        by_dimension.setdefault(key(row.get("dimension")), []).append(row)
    checked, dimension_states = [], {}
    for dimension in dimensions:
        candidates = by_dimension.get(key(dimension)) or [{}]
        checked_candidates = {}
        for candidate in candidates:
            answer = deepcopy(candidate)
            refs = sorted({(brief.get("fact_aliases") or {}).get(ref, ref) for ref in answer.get("fact_ids") or []})
            answer["fact_ids"] = refs
            grounded = bool(refs) and all(ref in facts and set(facts[ref].get("source_ids") or []) & sources
                                          and facts[ref].get("value") is not None for ref in refs)
            from .portfolio_evidence import material_fact_issues
            bad = [ref for ref in refs if facts.get(ref, {}).get("superseded_by") or
                (facts.get(ref, {}).get("review_dimensions") or {}).get("observation") == "unsupported" or
                material_fact_issues(facts.get(ref, {}))]
            status = answer.get("status") if grounded and answer.get("answer") else "unresolved"
            if bad:
                status = "partial" if len(bad) < len(refs) and grounded else "unresolved"
                answer["qualified_fact_ids"] = bad
            else:
                answer.pop("qualified_fact_ids", None)
            answer["support_status"] = "source_supported" if refs and all(facts.get(ref, {}).get("claim_status") == "supported" for ref in refs) else "unverified"
            if status not in {"answered", "partial", "conflicting", "unresolved"}:
                status = "unresolved"
            normalized = {**answer, "dimension": dimension, "status": status}
            identity = digest({"answer": " ".join(str(answer.get("answer") or "").split()), "facts": refs})
            # Repeated phase merges must not multiply the same proposition.
            previous = checked_candidates.get(identity)
            rank = {"unresolved": 0, "partial": 1, "answered": 2, "conflicting": 3}
            if previous is None or (rank[status], digest(normalized)) > (rank[previous["status"]], digest(previous)):
                checked_candidates[identity] = normalized
        ordered = [row for _, row in sorted(checked_candidates.items())]
        useful = [row for row in ordered if row["status"] != "unresolved"]
        retained = useful or ordered[:1]
        states = {row["status"] for row in retained}
        dimension_states[dimension] = ("conflicting" if "conflicting" in states or _numeric_disagreement(retained, facts)
            else "answered" if "answered" in states else "partial" if "partial" in states else "unresolved")
        checked.extend(retained)
    states = set(dimension_states.values())
    status = "answered" if states == {"answered"} else "conflicting" if "conflicting" in states else "partial" if states & {"answered", "partial"} else "unanswered"
    return {"status": status, "answers": checked,
            "missing_dimensions": [dimension for dimension, state in dimension_states.items() if state != "answered"]}


def normalize_questions(rows, evidence=None):
    grouped = {}
    for original in rows or []:
        if not isinstance(original, dict) or not isinstance(original.get("question"), str):
            continue
        row = deepcopy(original)
        for field in ("asset_classes", "required_dimensions", "play_ids", "component_ids", "component_names", "existing_fact_ids", "inspect_source_ids"):
            row[field] = [value.strip() for value in row.get(field) or [] if isinstance(value, str) and value.strip()] if isinstance(row.get(field), list) else []
        question = " ".join(row["question"].split())
        if not question or any(char in question for char in "{}[]"):
            continue
        if not row.get("material_reason") or not row.get("reuse_assessment") or not row.get("asset_classes"):
            continue
        row.update(question=question, kind="market_fact", critical_premise=row.get("critical_premise") is True)
        identity = {field: key(row.get(field)) for field in ("economic_question", "geography", "period", "horizon")}
        if not identity["economic_question"]:
            identity["economic_question"] = key(question)
        identity = observation_scope(row) or identity
        identifier = "question_" + digest(identity)[:20]
        row.update(id=identifier, required_dimensions=row.get("required_dimensions") or [question])
        if row.get("status") == "not_market":
            continue
        row.update(coverage(row, evidence or {}, row.get("answers")))
        if identifier in grouped:
            previous = grouped[identifier]
            previous["dimension_measurements"] = [*previous.get("dimension_measurements", []), *row.get("dimension_measurements", [])]
            for field in ("required_dimensions", "asset_classes", "play_ids", "component_ids", "existing_fact_ids"):
                previous[field] = list(dict.fromkeys([*previous.get(field, []), *row.get(field, [])]))
            previous["critical_premise"] = previous.get("critical_premise") is True or row.get("critical_premise") is True
            if row.get("decision_impact") == "high":
                previous["decision_impact"] = "high"
            previous["answers"] = [*previous.get("answers", []), *row.get("answers", [])]
            previous.update(coverage(previous, evidence or {}, previous["answers"]))
        else:
            grouped[identifier] = row
    return prioritize_searches(list(grouped.values()), {})


def provider_context(question, evidence):
    facts = {row.get("id"): row for row in evidence.get("facts", [])}
    for alias, canonical in (evidence.get("fact_aliases") or {}).items():
        if canonical in facts:
            facts[alias] = facts[canonical]
    return {**{field: deepcopy(question[field]) for field in
        ("topic", "geography", "period", "horizon", "required_dimensions", "reuse_assessment") if question.get(field)},
        "known_observations": [{field: deepcopy(facts[ref].get(field)) for field in
            ("metric", "value", "unit", "benchmark", "observed_at", "published_at", "measurement")}
            for ref in question.get("existing_fact_ids", []) if ref in facts]}


def merge_question(previous, incoming, evidence):
    incoming = deepcopy(incoming)
    if previous:
        known = {key(value): value for value in previous.get("required_dimensions", [])}
        aliases = {key(row.get("dimension")): known[key(row.get("existing_dimension"))]
                   for row in incoming.get("dimension_aliases", []) if isinstance(row, dict)
                   and key(row.get("existing_dimension")) in known}
        incoming["required_dimensions"] = [aliases.get(key(value), value) for value in incoming.get("required_dimensions", [])]
        for answer in incoming.get("answers", []):
            if isinstance(answer, dict) and key(answer.get("dimension")) in aliases:
                answer["dimension"] = aliases[key(answer["dimension"])]
        incoming["id"] = previous["id"]
    result = {**deepcopy(previous or {}), **deepcopy(incoming)}
    if previous:
        for field in ("id", "question", "topic", "economic_question", "observation_scope", "geography", "period", "horizon"):
            if previous.get(field):
                result[field] = deepcopy(previous[field])
        result["question_aliases"] = list(dict.fromkeys([*previous.get("question_aliases", []),
            *([incoming["question"]] if incoming.get("question") and incoming["question"] != previous.get("question") else [])]))
        result["critical_premise"] = previous.get("critical_premise") is True or incoming.get("critical_premise") is True
    bindings = {(key(row.get("dimension")), digest(row.get("scope"))): deepcopy(row)
        for row in [*(previous or {}).get("dimension_measurements", []), *incoming.get("dimension_measurements", [])]
        if isinstance(row, dict)}
    result["dimension_measurements"] = list(bindings.values())
    for field in ("required_dimensions", "asset_classes", "play_ids", "component_ids", "existing_fact_ids", "searched_dimensions"):
        result[field] = list(dict.fromkeys([*(previous or {}).get(field, []), *incoming.get(field, [])]))
    result.update(coverage(result, evidence, [*(previous or {}).get("answers", []), *incoming.get("answers", [])]))
    return result


def prioritize_searches(questions, registry):
    """Concrete decision consequences first; preserve the planner's order within a tier."""
    return sorted(questions, key=lambda row: (
        not bool(str(row.get("decision_consequence") or "").strip()),
        not row.get("critical_premise"), {"high": 0, "medium": 1, "low": 2}.get(row.get("decision_impact"), 1),
        row.get("decision_dependency") == "market_quote",
    ))


def refresh_signed_evidence(brief, *, detached=True):
    from .portfolio_evidence import normalize_facts, fact_fingerprint, apply_fact_checks
    result = deepcopy(brief) if detached else {**brief, "facts": list(brief.get("facts", []))}
    repairable = {"Claimed numeric value is not in the supporting excerpt; a derivation must be reviewed",
                  "Supporting excerpt not found in retrieved source", "Missing observed_at", "Invalid observed_at",
                  "published_at is after the research cutoff", "Referenced source was published after the research cutoff"}
    for index, fact in enumerate(result.get("facts", [])):
        if not repairable.intersection(fact.get("verification_issues", [])):
            continue
        if not detached:
            fact = deepcopy(fact)
            result["facts"][index] = fact
        checked = normalize_facts([fact], brief.get("source_packet") or {})[0]
        review = fact.get("claim_review") or {}
        if review.get("fact_hash") == fact_fingerprint(fact) and review.get("checks"):
            checked = apply_fact_checks([fact], [{"fact_id": fact["id"], "checks": review["checks"], "reason": review.get("reason"),
                "check_contract": review.get("check_contract"), "check_model": review.get("check_model")}],
                brief.get("source_packet") or {})[0]
        # Repair presentation only. Preserve reviewer findings, metadata and the raw source.
        fact["verification_issues"] = [issue for issue in fact["verification_issues"]
            if issue not in repairable or issue in checked["verification_issues"]]
        for field in ("value_derivation", "source_text_normalization"):
            if field in checked:
                fact[field] = checked[field]
        if checked.get("claim_review"):
            for field in ("claim_review", "claim_status", "review_dimensions", "availability_status", "evidence_status"):
                fact[field] = checked[field]
    return result


def remaining_search(question, *, inspect_source_ids=()):
    """One search per missing dimension and cutoff; failures may retry without forgetting answers."""
    searched = {key(value) for value in question.get("searched_dimensions", [])}
    dimensions = [value for value in question.get("missing_dimensions", []) if key(value) not in searched]
    if not dimensions and not (inspect_source_ids and question.get("missing_dimensions")):
        return None
    result = deepcopy(question)
    result["inspection_only"] = not dimensions
    result["inspect_source_ids"] = list(inspect_source_ids)
    result["required_dimensions"] = dimensions or list(question["missing_dimensions"])
    dimensions = result["required_dimensions"]
    if dimensions != question.get("required_dimensions"):
        result["question"] = f"{question.get('topic') or 'Market evidence'}: establish " + "; ".join(dimensions) + "."
    result["existing_fact_ids"] = list(dict.fromkeys([*question.get("existing_fact_ids", []),
        *(ref for answer in question.get("answers", []) for ref in answer.get("fact_ids", []))]))
    return result


def research_readthrough(evidence, decisions=None):
    """Surface new observations and dissent ahead of the earlier market narrative."""
    from .portfolio_judgment import linked_facts
    referenced = linked_facts(decisions or {})
    rows = [{"question_id": row.get("id") or row["question_id"], "question": row["question"], "asset_classes": row.get("asset_classes", []),
             **{field: deepcopy(row[field]) for field in ("topic", "economic_question", "observation_scope", "geography", "period", "horizon", "play_ids", "component_ids", "critical_premise", "reuse_question_id", "decision_consequence", "decision_impact") if field in row},
             "material_reason": row.get("material_reason"), "status": row.get("status"),
             "answers": [{field: answer[field] for field in ("dimension", "status", "answer", "fact_ids", "support_status", "qualified_fact_ids") if field in answer}
                         for answer in row.get("answers", []) if answer.get("answer")],
             "missing_dimensions": row.get("missing_dimensions", []),
             "not_cited_in_proposals": bool(decisions) and not bool(referenced & {
                 ref for answer in row.get("answers", []) for ref in answer.get("fact_ids", [])})}
            for row in evidence.get("research_questions", []) if row.get("id") or row.get("question_id")]
    registry = {row["question_id"]: row for row in rows}
    neighbours = {identifier: set() for identifier in registry}
    for row in rows:
        parent = row.get("reuse_question_id")
        if parent in registry and parent != row["question_id"]:
            neighbours[parent].add(row["question_id"])
            neighbours[row["question_id"]].add(parent)
    for row in rows:
        related, pending = set(), list(neighbours[row["question_id"]])
        while pending:
            identifier = pending.pop()
            if identifier == row["question_id"] or identifier in related:
                continue
            related.add(identifier)
            pending.extend(neighbours[identifier] - related)
        if not related:
            continue
        row["related_question_ids"] = sorted(related)
        # Explicit continuity is not permission to merge different measurement scopes.
        row["related_answer_ids"] = [identifier for identifier in sorted(related)
            if any(answer.get("fact_ids") and answer.get("status") in {"answered", "partial", "conflicting"}
                   for answer in registry[identifier]["answers"])]
        if row["related_answer_ids"]:
            row["scope_status"] = row["status"]
            if row["status"] == "unanswered":
                row["status"] = "partial"
            row["coverage_note"] = "Read the related answer records in this packet. Preserve their scope and qualifications; missing original dimensions do not mean no evidence was supplied."
    return rows


def current_research_questions(evidence):
    """Recompute coverage from saved answers without changing the research record."""
    validated = []
    for original in evidence.get("research_questions", []):
        if original.get("status") == "not_market":
            continue
        row = deepcopy(original)
        row.update(coverage(row, evidence, row.get("answers")))
        validated.append(row)
    current = {row["question_id"]: row for row in research_readthrough({"research_questions": validated})}
    for row in validated:
        view = current.get(row.get("id") or row.get("question_id"), {})
        row.update({field: view[field] for field in
            ("status", "scope_status", "coverage_note", "related_answer_ids") if field in view})
    return validated


def qualify_research_dependencies(proposal, evidence):
    """Record remaining support gaps; coverage alone does not decide whether to trade."""
    result = deepcopy(proposal)
    unresolved = [row for row in current_research_questions(evidence) if row.get("status") != "answered"]
    for play in result.get("play_assessments", []):
        for leg in play.get("legs", []):
            gaps = [row for row in unresolved if row["id"] in (leg.get("research_question_ids") or []) or
                    (play.get("play_id") in row.get("play_ids", []) and
                    leg.get("component_id") in row.get("component_ids", []))]
            leg["research_gaps"] = [{"question_id": row["id"], "question": row["question"], "status": row["status"]} for row in gaps]
            if any(row.get("critical_premise") is True for row in gaps):
                leg.setdefault("reported_judgment", {"score": leg.get("score"), "verdict": leg.get("verdict")})
                if isinstance(leg.get("score"), (int, float)) and not isinstance(leg["score"], bool):
                    leg.update(confidence="low", assessment_status="provisional")
                else:
                    leg.update(verdict="needs_research", confidence="unassessed", assessment_status="research_incomplete")
        if any(leg.get("assessment_status") in {"missing", "research_incomplete", "provisional"} for leg in play.get("legs", [])):
            play.setdefault("reported_judgment", {"score": play.get("score"), "verdict": play.get("verdict")})
            play.update(coverage_status="incomplete", assessment_status="provisional" if play.get("score") is not None else "research_incomplete")
            if play.get("score") is None:
                play["verdict"] = "needs_research"
    from .portfolio_exposures import decision_relationships
    for target in result.get("asset_class_targets", []):
        # Retire the old coverage-derived trading label, including on resumed proposals.
        target.pop("action_readiness", None)
        target.pop("research_gaps", None)
        assets = decision_relationships(target)["assets"]
        gaps = [row for row in unresolved if row["id"] in (target.get("research_question_ids") or []) or
                bool(assets & decision_relationships({"asset_classes": row.get("asset_classes", [])})["assets"])]
        if gaps:
            target["research_gaps"] = [{"question_id": row["id"], "question": row["question"],
                **{field: row[field] for field in ("status", "scope_status", "coverage_note", "related_answer_ids", "missing_dimensions", "decision_consequence") if field in row}}
                for row in gaps]
    return result
