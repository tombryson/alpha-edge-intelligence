"""Keep usable model output; contain missing review and enrichment fields locally."""

from copy import deepcopy
import json
import re

from .portfolio_evidence import review_fields

VERDICTS = {"supported", "unsupported", "unresolved"}
MISSING = object()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("Non-finite replacement: " + value)


def parse_json_object(text):
    """Repair only JSON presentation: fences, literal control characters and trailing commas."""
    raw = str(text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
        raw = re.sub(r"\s*```$", "", raw)
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < start:
        return None
    raw = raw[start:end + 1]
    def decode(value):
        result = json.loads(value, strict=False, object_pairs_hook=_unique_object)
        return result if isinstance(result, dict) else None
    try:
        return decode(raw)
    except ValueError:
        pass
    output, quoted, escaped = [], False, False
    for index, char in enumerate(raw):
        if quoted:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        else:
            if char == '"':
                quoted = True
            if char == ",":
                following = index + 1
                while following < len(raw) and raw[following].isspace():
                    following += 1
                if following < len(raw) and raw[following] in "}]":
                    continue
            output.append(char)
    try:
        return decode("".join(output))
    except ValueError:
        return None


def field_repair_prompt(prompt, value, errors):
    """Ask only for invalid top-level fields; the caller merges into the retained object."""
    if not isinstance(value, dict):
        return None
    path_repair = row_repair_prompt(prompt, value, errors)
    if path_repair:
        return path_repair
    schema = prompt.get("required_schema") or {}
    fields = {key for key, template in schema.items() if key not in value
        or (isinstance(template, (dict, list)) and not isinstance(value[key], type(template)))}
    fields.update(key for key in schema if any(re.search(r"\b" + re.escape(key) + r"\b", error) for error in errors))
    if not fields:
        return None
    from .portfolio_requests import observation_brief, reader_decision
    # Keep task constraints, but never replay receipts or the original giant
    # proposal for a missing supplementary section.
    context = {key: deepcopy(prompt[key]) for key in ("task", "contract", "research_cutoff", "rules",
        "independent_context", "investment_brief", "current_portfolio", "portfolio_context", "recorded_allocation",
        "assigned_allocations", "investment_plays", "query", "question", "scope", "review_scope") if key in prompt}
    for key in ("proposal", "provisional_recommendation", "final_recommendation", "independent_ideal", "current_assessment"):
        if isinstance(prompt.get(key), dict):
            context[key] = reader_decision(prompt[key])
    packet = prompt.get("evidence_brief") or prompt.get("evidence")
    if isinstance(packet, dict):
        context["evidence_brief"] = observation_brief(packet)
    result = {**context, "required_schema": {key: schema[key] for key in schema if key in fields},
        "validation_errors": errors, "invalid_fields": {key: deepcopy(value[key]) for key in fields if key in value},
        "retained_fields": sorted(set(value) - fields)}
    result["rules"] = [*result.get("rules", []),
        "Correct only the requested fields using the supplied evidence. All other fields are already saved and will be retained; do not reproduce them. Never invent missing financial facts."]
    return result


def row_repair_prompt(prompt, value, errors):
    """Repair exact invalid row fields, retaining all accepted sibling decisions locally."""
    paths = set()
    schema = prompt.get("required_schema") or {}
    for error in errors:
        for match in re.finditer(r"response((?:\.[A-Za-z_]\w*|\[\d+\])+)", error):
            parts = re.findall(r"\.([A-Za-z_]\w*)|\[(\d+)\]", match[1])
            path = tuple(name if name else int(index) for name, index in parts)
            if any(isinstance(part, int) for part in path):
                paths.add(path)
    rows = value.get("asset_class_targets")
    if isinstance(rows, list) and "asset_class_targets" in schema:
        import math
        numeric_errors = any("Point allocation totals" in error for error in errors) and all(
            isinstance(row, dict) and isinstance(row.get("target_pct"), (int, float))
            and not isinstance(row["target_pct"], bool) and math.isfinite(row["target_pct"]) for row in rows)
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            asset = str(row.get("asset_class") or "").upper().replace("_", "").replace("-", "")
            matching = [error for error in errors if error.startswith(asset + ":")]
            if numeric_errors or any("numeric ranges" in error or "allocation range" in error for error in matching):
                paths.update(("asset_class_targets", index, field) for field in ("min_pct", "target_pct", "max_pct"))
            for field in row:
                if any(re.search(r"\b" + re.escape(field) + r"\b", error) for error in matching):
                    paths.add(("asset_class_targets", index, field))
    if not paths:
        return None
    # Parent repairs subsume invalid child fields, never competing patches.
    paths = {path for path in paths if not any(path[:len(parent)] == parent and path != parent for parent in paths)}
    affected, allowed = [], []
    for path in sorted(paths, key=repr):
        node, template = value, schema
        try:
            for part in path[:-1]:
                node = node[part]
                template = template[0] if isinstance(part, int) else template[part]
            if isinstance(template, dict) and path[-1] not in template:
                continue
            current = node.get(path[-1]) if isinstance(node, dict) else node[path[-1]]
            expected = template[0] if isinstance(path[-1], int) else template[path[-1]]
            allowed.append({"path": list(path), "current_value": deepcopy(current), "expected": deepcopy(expected)})
            if isinstance(path[1] if len(path) > 1 else None, int):
                affected.append(value[path[0]][path[1]])
        except (KeyError, IndexError, TypeError):
            continue
    if not allowed:
        return None
    from .portfolio_tasks import allocation_context, evidence_for_decisions
    evidence = prompt.get("evidence_brief") or prompt.get("evidence") or {}
    if evidence.get("evidence_view") == "observation-index-v1":
        from .portfolio_requests import expand_observations
        evidence = expand_observations(evidence)
    context = [{key: deepcopy(row[key]) for key in ("asset_class", "rationale", "fact_ids", "research_question_ids") if key in row}
               for row in affected if isinstance(row, dict)]
    return {"task": "Correct invalid fields in retained analysis", "repair_contract": "portfolio-path-repair-v1",
        "required_schema": {"patches": [{"path": ["exact field names and indexes from allowed_repairs"],
            "value_json": "JSON-encoded replacement value, including quotes for strings"}]},
        "allowed_repairs": allowed, "validation_errors": errors, "affected_cases": context,
        "recorded_allocation": allocation_context(value), "evidence_brief": evidence_for_decisions(evidence, affected),
        "rules": ["Return only patches to allowed_repairs paths. All other analysis is saved and cannot be overwritten.",
            "Correct the model's decision, not the source data. Do not invent missing financial facts. Keep the complete allocation funded at 100% and ranges ordered."]}


def apply_row_repairs(retained, response, repair):
    allowed = {tuple(row["path"]) for row in repair["allowed_repairs"]}
    result, seen = deepcopy(retained), set()
    patches = response.get("patches")
    if not isinstance(patches, list) or not patches:
        raise ValueError("Row repair returned no patches")
    for patch in patches:
        path = tuple(patch.get("path", [])) if isinstance(patch, dict) else ()
        if not all(type(part) in (str, int) for part in path):
            raise ValueError("Invalid repair path")
        if path not in allowed or path in seen:
            raise ValueError("Row repair targeted an unassigned or duplicate path")
        seen.add(path)
        replacement = json.loads(patch["value_json"], object_pairs_hook=_unique_object,
            parse_constant=_reject_constant)
        node = result
        for part in path[:-1]:
            node = node[part]
        node[path[-1]] = replacement
    return result


def _completed_array_items(raw, position, decoder):
    if raw[position:position + 1] != "[":
        return []
    result = []
    position += 1
    while position < len(raw):
        while position < len(raw) and raw[position].isspace():
            position += 1
        try:
            value, position = decoder.raw_decode(raw, position)
        except ValueError:
            break
        while position < len(raw) and raw[position].isspace():
            position += 1
        if raw[position:position + 1] not in {",", "]"}:
            break
        result.append(value)
        if raw[position:position + 1] == "]":
            break
        position += 1
    return result


def completed_json_fields(text, *, partial_array_fields=()):
    """Read received values, optionally complete members of named arrays; never invent closing data."""
    raw = str(text or "")
    position = raw.find("{") + 1
    if position == 0:
        return None
    decoder = json.JSONDecoder(strict=False, object_pairs_hook=_unique_object)
    result = {}
    try:
        while position < len(raw):
            while position < len(raw) and raw[position].isspace():
                position += 1
            key, position = decoder.raw_decode(raw, position)
            if not isinstance(key, str) or key in result:
                return None
            while position < len(raw) and raw[position].isspace():
                position += 1
            if raw[position:position + 1] != ":":
                break
            position += 1
            while position < len(raw) and raw[position].isspace():
                position += 1
            try:
                value, position = decoder.raw_decode(raw, position)
            except ValueError:
                # Only explicitly requested collection fields can retain a received
                # prefix; every member still needs its own closing delimiter.
                if key in partial_array_fields:
                    items = _completed_array_items(raw, position, decoder)
                    if items:
                        result[key] = items
                break
            while position < len(raw) and raw[position].isspace():
                position += 1
            # raw_decode accepts numeric prefixes such as the 1 in 1e. A received
            # value is complete only when its surrounding JSON supplies a delimiter.
            if raw[position:position + 1] not in {",", "}"}:
                break
            result[key] = value
            if raw[position:position + 1] != ",":
                break
            position += 1
    except (ValueError, IndexError):
        pass
    return result or None


def retain_terminal_review(response, prompt, validator):
    """Retain complete findings, without claiming the interrupted review covered its scope."""
    schema = prompt.get("required_schema") or {}
    if (prompt.get("contract") != "independent-portfolio-v1" or "findings" not in schema
            or prompt.get("update_contract") or response.get("outcome_uncertain")
            or response.get("finish_reason") != "error"):
        return None, []
    parsed = parse_json_object(response.get("content"))
    complete_fields = parsed or completed_json_fields(response.get("content")) or {}
    value = parsed or completed_json_fields(response.get("content"), partial_array_fields={"findings"}) or complete_fields
    findings = (value or {}).get("findings")
    if not isinstance(findings, list) or not findings:
        return None, []
    # Do not complete an unfinished finding or supply its missing factual argument.
    for row in findings:
        if (not isinstance(row, dict) or not isinstance(row.get("argument"), str) or not row["argument"].strip()
                or not isinstance(row.get("asset_class"), str) or not row["asset_class"].strip()
                or row.get("kind") not in {"factual_correction", "investment_disagreement", "research_gap"}
                or not isinstance(row.get("fact_ids"), list)
                or any(not isinstance(identifier, str) for identifier in row["fact_ids"])):
            return None, []
    recovered, warnings = recover_optional_fields(value, prompt)
    if validator(recovered, prompt):
        return None, []
    recovered.update(review_completion="partial", review_coverage={
        "status": "incomplete", "assigned_scope": deepcopy(prompt.get("review_scope") or {}),
        "missing_fields": sorted(set(schema) - set(value)),
        "incomplete_fields": sorted(set(value) - set(complete_fields)), "retained_findings": len(findings)})
    warnings.append({"detail": "The provider ended this review with an error. Fully received findings were retained; "
        "the assigned review is incomplete, and absent objections or scenarios must not be treated as clearance."})
    return recovered, warnings


def _review_rows(value):
    rows, duplicates = {}, set()
    candidates = (value or {}).get("fact_checks", [])
    for row in candidates if isinstance(candidates, list) else []:
        if not isinstance(row, dict) or not isinstance(row.get("fact_id"), str):
            continue
        identifier = row["fact_id"]
        if identifier in rows:
            duplicates.add(identifier)
        rows[identifier] = deepcopy(row)
        # Locally unresolved fallback fields remain repairable on later resumes.
        issues = row.get("review_issues")
        for issue in issues if isinstance(issues, list) else []:
            fields = issue.get("fields") if isinstance(issue, dict) else []
            for field in fields if isinstance(fields, list) else []:
                if not isinstance(field, str):
                    continue
                if field == "reason":
                    rows[identifier].pop("reason", None)
                elif isinstance(rows[identifier].get("checks"), dict):
                    rows[identifier]["checks"].pop(field, None)
    return {key: row for key, row in rows.items() if key not in duplicates}


def review_problems(value, prompt):
    rows = _review_rows(value)
    problems = {}
    for fact in (prompt.get("evidence") or {}).get("facts", []):
        row = rows.get(fact["id"], {})
        checks = row.get("checks") if isinstance(row.get("checks"), dict) else {}
        missing = [key for key in review_fields(fact) if not isinstance(checks.get(key), str) or checks[key] not in VERDICTS]
        if not isinstance(row.get("reason"), str) or not row["reason"].strip():
            missing.append("reason")
        if missing:
            problems[fact["id"]] = missing
    return problems


def merge_reviews(retained, incoming, prompt):
    """A repair can fill gaps, but cannot overwrite accepted verdicts or add facts."""
    old, new = _review_rows(retained), _review_rows(incoming)
    rows = []
    for fact in (prompt.get("evidence") or {}).get("facts", []):
        identifier = fact["id"]
        row = deepcopy(old.get(identifier, {"fact_id": identifier}))
        candidate = new.get(identifier, {})
        checks = row.get("checks") if isinstance(row.get("checks"), dict) else {}
        updates = candidate.get("checks") if isinstance(candidate.get("checks"), dict) else {}
        for key in review_fields(fact):
            if not isinstance(checks.get(key), str) or checks[key] not in VERDICTS:
                if isinstance(updates.get(key), str) and updates[key] in VERDICTS:
                    checks[key] = updates[key]
        row["checks"] = checks
        row.pop("review_issues", None)
        if not isinstance(row.get("reason"), str) or not row["reason"].strip():
            row["reason"] = candidate.get("reason")
        if not row.get("correction") and isinstance(candidate.get("correction"), dict):
            row["correction"] = deepcopy(candidate["correction"])
        rows.append(row)
    return {"fact_checks": rows}


def review_repair_prompt(prompt, retained):
    problems = review_problems(retained, prompt)
    repair = deepcopy(prompt)
    evidence = repair["evidence"]
    evidence["facts"] = [fact for fact in evidence["facts"] if fact["id"] in problems]
    refs = {ref for fact in evidence["facts"] for ref in fact.get("source_ids", [])}
    if isinstance(evidence.get("source_packet"), dict):
        evidence["source_packet"]["sources"] = [source for source in evidence["source_packet"].get("sources", []) if source["id"] in refs]
    repair["repair_fields"] = problems
    repair["previous_reviews"] = [row for row in retained.get("fact_checks", []) if row["fact_id"] in problems]
    repair["rules"] = [*repair.get("rules", []),
        "Repair only the listed fact IDs and fields in repair_fields. Other accepted reviews are retained unchanged.",
        "Return the requested fact_checks objects. Use unresolved when the source cannot establish a verdict; include a reason."]
    return repair


def recover_reviews(value, prompt):
    problems = review_problems(value, prompt)
    rows = _review_rows(value)
    warnings, recovered = [], []
    for fact in (prompt.get("evidence") or {}).get("facts", []):
        identifier = fact["id"]
        row = deepcopy(rows.get(identifier, {"fact_id": identifier, "checks": {}}))
        fields = row.get("checks") if isinstance(row.get("checks"), dict) else {}
        missing = problems.get(identifier, [])
        # An unexplained verdict must not become supported through our own fallback text.
        checks = {key: fields.get(key) if key not in missing and "reason" not in missing else "unresolved" for key in review_fields(fact)}
        reason = row.get("reason") if "reason" not in missing else "The model did not provide a source-review explanation."
        recovered.append({**({"correction": deepcopy(row["correction"])} if isinstance(row.get("correction"), dict) else {}),
                          "fact_id": identifier, "checks": checks, "reason": reason,
                          "review_issues": [{"fields": missing, "reason": "Missing model review; not verified"}] if missing else []})
        if missing:
            warnings.append({"fact_id": identifier, "fields": missing,
                "detail": f"{identifier}: review incomplete for {', '.join(missing)}; affected checks remain unresolved."})
    return {"fact_checks": recovered}, warnings


def _empty(template):
    if isinstance(template, dict):
        return {key: _empty(value) for key, value in template.items()}
    return [] if isinstance(template, list) else None


def _optional_shape(value, template, path, warnings):
    if isinstance(template, dict):
        if not isinstance(value, dict):
            warnings.append({"field": path, "detail": f"{path}: details were not supplied."})
            return _empty(template)
        result = deepcopy(value)
        for key, child in template.items():
            result[key] = _optional_shape(value.get(key, MISSING), child, f"{path}.{key}", warnings)
        return result
    if isinstance(template, list):
        if not isinstance(value, list):
            warnings.append({"field": path, "detail": f"{path}: details were not supplied."})
            return []
        return [_optional_shape(row, template[0], f"{path}[{i}]", warnings) for i, row in enumerate(value)] if template else deepcopy(value)
    if value is MISSING or isinstance(value, (dict, list)):
        warnings.append({"field": path, "detail": f"{path}: value is unknown."})
        return None
    return value


def recover_optional_fields(value, prompt, *, exhausted=False):
    """Normalize optional metadata only; never fabricate facts, weights or source verdicts."""
    schema = prompt.get("required_schema") or {}
    warnings = []
    if prompt.get("update_contract") == "portfolio-review-delta-v1":
        if not isinstance(value, dict) or not any(key in value for key in schema):
            return value, warnings
        return {"finding_updates": [], "play_updates": [], **deepcopy(value)}, warnings
    if prompt.get("update_contract") == "portfolio-final-delta-v1":
        if not isinstance(value, dict) or not any(key in value for key in schema):
            return value, warnings
        result = deepcopy(value)
        for key, default in (("reason", None), ("target_updates", []), ("removed_target_ids", []), ("updates", {})):
            if key not in result:
                result[key] = deepcopy(default)
                warnings.append({"field": key, "detail": "Omitted update retained the saved decision; no value was invented."})
        # Absence is meaningful in a delta. Never materialise nested nulls or empty lists.
        return result, warnings
    if "allocation_details" in schema:
        if not isinstance(value, dict) and not exhausted:
            return value, warnings
        candidates = (value or {}).get("allocation_details") or []
        by_asset, duplicates = {}, set()
        for row in candidates if isinstance(candidates, list) else []:
            if not isinstance(row, dict) or not isinstance(row.get("asset_class"), str):
                continue
            asset = row["asset_class"]
            if asset in by_asset:
                duplicates.add(asset)
            by_asset[asset] = row
        fields = schema["allocation_details"][0]
        expected = [row["asset_class"] for row in prompt.get("assigned_allocations", [])]
        unexpected = set(by_asset) - set(expected)
        if unexpected:
            warnings.append({"detail": "Unassigned asset details were retained only in the raw response: " + ", ".join(sorted(unexpected))})
        result = []
        for asset in expected:
            candidate = by_asset.get(asset, {}) if asset not in duplicates else {}
            extras = set(candidate) - set(fields)
            if extras:
                warnings.append({"asset_class": asset, "detail": f"{asset}: ignored extra detail fields {', '.join(sorted(extras))}; recorded allocation unchanged."})
            row = {"asset_class": asset}
            for key, template in fields.items():
                if key != "asset_class":
                    row[key] = _optional_shape(candidate.get(key, MISSING), template, f"{asset}.{key}", warnings)
            result.append(row)
        return {"allocation_details": result}, warnings
    # These contracts have useful primary output independent of their optional sections.
    recognized = (any(key in schema for key in ("asset_class_targets", "macro_scorecard", "asset_class_comments", "question_answers"))
                  or prompt.get("contract") == "independent-portfolio-v1"
                  or str(prompt.get("research_contract") or "").startswith("question-led-research-v"))
    if not recognized or not isinstance(value, dict) or not value:
        return value, warnings
    result = deepcopy(value)
    for key, template in schema.items():
        if key == "asset_class_targets":
            if isinstance(result.get(key), list) and template and isinstance(template[0], dict):
                for index, row in enumerate(result[key]):
                    if isinstance(row, dict):
                        for field, shape in template[0].items():
                            if field not in {"asset_class", "min_pct", "target_pct", "max_pct"}:
                                row[field] = _optional_shape(row.get(field, MISSING), shape, f"asset_class_targets[{index}].{field}", warnings)
            continue
        result[key] = _optional_shape(result.get(key, MISSING), template, key, warnings)
    if prompt.get("contract") == "independent-portfolio-v1":
        from .portfolio_independent import complete_play_assessments
        if "play_assessments" in schema:
            normalized = complete_play_assessments(prompt.get("investment_plays") or [], result.get("play_assessments"),
                                                  brief=prompt.get("play_assessment_mode") == "brief")
            old = result.get("play_assessments") or []
            if len(normalized) != len(old) or any(not isinstance(a, dict) or any(a.get(key) != b.get(key)
                    for key in ("play_id", "score", "verdict", "reason")) for a, b in zip(old, normalized)):
                warnings.append({"field": "play_assessments", "detail": "Missing or invalid play assessments remain unassessed; other analysis is retained."})
            result["play_assessments"] = normalized
        if "current_assessment" in schema:
            existing = {row.get("asset_class"): row for row in result.get("current_assessment") or [] if isinstance(row, dict) and isinstance(row.get("asset_class"), str)}
            for row in (prompt.get("current_portfolio") or {}).get("current_asset_classes", []):
                if row["asset_class"] not in existing:
                    warnings.append({"field": "current_assessment", "detail": f"{row['asset_class']}: current exposure not assessed; retained for review."})
            result["current_assessment"] = [existing.get(row["asset_class"]) or {
                "asset_class": row["asset_class"], "display_name": row.get("display_name"), "action": "REVIEW",
                "rationale": "This exposure has not yet received a substantive assessment.", "thesis_conviction": "UNASSESSED"}
                for row in (prompt.get("current_portfolio") or {}).get("current_asset_classes", [])]
    return result, warnings
