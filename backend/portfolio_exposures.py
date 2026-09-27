"""Explicit, open-ended relationships between portfolio proposals and holdings."""

from copy import deepcopy

from .portfolio_decisions import asset_key, number


LINK_SCHEMA = {"view": "ideal | current | holdings", "asset_class": "exact source exposure identifier",
               "relationship": "equivalent | partial_overlap | substitute", "share_pct": "share of source exposure, 0-100, or null",
               "capital_component": "true only for a verified constituent capital share, false for shared risk sensitivity",
               "reason": "why the instruments are equivalent, overlap, or are alternatives"}


def decision_relationships(value):
    """Shared evidence relationships; aliases expand access, never transfer capital."""
    result = {"assets": set(), "questions": set(), "plays": set(), "components": set()}
    def visit(item):
        if isinstance(item, list):
            for child in item:
                visit(child)
        elif isinstance(item, dict):
            for field in ("asset_class", "display_name", "source_asset_class"):
                if isinstance(item.get(field), str) and item[field]:
                    result["assets"].add(asset_key(item[field]))
            for field, group in (("asset_classes", "assets"), ("aliases", "assets"),
                                 ("research_question_ids", "questions"), ("play_ids", "plays"), ("component_ids", "components")):
                refs = item.get(field)
                for ref in refs if isinstance(refs, list) else []:
                    if isinstance(ref, str) and ref:
                        result[group].add(asset_key(ref) if group == "assets" else ref)
            for field, group in (("question_id", "questions"), ("play_id", "plays"), ("component_id", "components")):
                if isinstance(item.get(field), str) and item[field]:
                    result[group].add(item[field])
            for child in item.values():
                if isinstance(child, (dict, list)):
                    visit(child)
    visit(value)
    return result


def reference_links(proposal, view, source_rows):
    sources = {asset_key(row.get("asset_class")): row for row in source_rows}
    declarations = {asset_key(row.get("asset_class")): row.get("baseline_links", [])
                    for row in proposal.get("reconciliation", []) if isinstance(row, dict)}
    links, issues, used = {}, [], {}
    for row in proposal.get("asset_class_targets", []):
        target = asset_key(row.get("asset_class"))
        declared = row.get("baseline_links") or declarations.get(target) or []
        explicit = [link for link in declared if isinstance(link, dict) and link.get("view") == view]
        if not explicit and target in sources:
            explicit = [{"asset_class": sources[target]["asset_class"], "relationship": "equivalent", "reason": "Same exposure identifier"}]
        accepted = []
        seen_links = set()
        for link in explicit:
            key = asset_key(link.get("asset_class"))
            relation = link.get("relationship")
            if view == "holdings" and row.get("position_identity") == "new" and relation in {"substitute", "partial_overlap"} and link.get("capital_component") is not True:
                continue
            if relation == "substitute":
                continue  # Alternatives are compared, never counted as the same capital.
            share = 100.0 if relation == "equivalent" else number(link.get("share_pct"))
            identity = (key, relation, share)
            if identity in seen_links:
                continue
            seen_links.add(identity)
            if key not in sources or relation not in {"equivalent", "partial_overlap"} or share is None or not 0 < share <= 100:
                issues.append(f"{row.get('asset_class')}: unresolved {view} exposure relationship")
                continue
            if view == "holdings" and relation == "partial_overlap" and link.get("capital_component") is not True:
                issues.append(f"{row.get('asset_class')}: shared risk does not establish a transferable share of current capital")
                continue
            source = sources[key]
            if view == "holdings":
                # Only the input book can establish capital ownership. A reviewer
                # may describe economic overlap but cannot attest its own mapping.
                aliases = {asset_key(name) for name in source.get("aliases") or [] if isinstance(name, str)}
                if relation == "equivalent" and target not in {key, *aliases}:
                    issues.append(f"{row.get('asset_class')}: proposed equivalence to {source['asset_class']} is not established by the holdings record")
                    continue
                if relation == "partial_overlap":
                    components = [part for part in source.get("capital_components") or [] if isinstance(part, dict)
                                  and asset_key(part.get("asset_class")) == target]
                    if len(components) != 1 or number(components[0].get("share_pct")) != share:
                        issues.append(f"{row.get('asset_class')}: the holdings record does not establish this capital component and share")
                        continue
            source_type = (source.get("implementation") or {}).get("instrument_type")
            target_type = (row.get("implementation") or {}).get("instrument_type")
            if relation == "equivalent" and source_type and target_type and asset_key(source_type) != asset_key(target_type):
                issues.append(f"{row.get('asset_class')}: equivalence conflicts with the recorded instrument types")
                continue
            accepted.append({**link, "source_key": key, "share_pct": share})
            used[key] = used.get(key, 0) + share
        links[target] = accepted
    overused = {key for key, share in used.items() if share > 100.00001}
    for key in overused:
        issues.append(f"{sources[key]['asset_class']}: {view} exposure is attributed more than once")
    if overused:
        links = {key: [link for link in values if link["source_key"] not in overused] for key, values in links.items()}
    return links, issues


def reconcile_references(proposal, ideal, current):
    result = deepcopy(proposal)
    rows = {asset_key(row.get("asset_class")): row for row in result.get("reconciliation", []) if isinstance(row, dict)}
    issues = []
    for view, baseline in (("ideal", ideal), ("current", current)):
        sources = {asset_key(row.get("asset_class")): row for row in baseline.get("asset_class_targets", [])}
        links, errors = reference_links(result, view, list(sources.values()))
        issues.extend(errors)
        for target in result.get("asset_class_targets", []):
            key = asset_key(target.get("asset_class"))
            row = rows.setdefault(key, {"asset_class": target["asset_class"]})
            values = [number(sources[link["source_key"]].get("target_pct")) for link in links.get(key, [])]
            value = sum(weight * link["share_pct"] / 100 for weight, link in zip(values, links[key])) if values and all(x is not None for x in values) else None
            field = view + "_reference_pct"
            if row.get(field) is not None and number(row[field]) != value:
                row.setdefault("reported_references", {})[field] = row[field]
                if value is None:
                    issues.append(f"{target['asset_class']}: the stated {view} comparison needs an explicit exposure relationship")
            row[field] = value
    result["reconciliation"] = list(rows.values())
    result["comparison_issues"] = list(dict.fromkeys(issues))
    return result


def economic_case_aliases(ideal, current, snapshot):
    """Group declared equivalences for review, without merging weights or holdings."""
    views = {"ideal": ideal.get("asset_class_targets", []), "current": current.get("asset_class_targets", []),
             "holdings": snapshot.get("asset_classes", [])}
    parent = {asset_key(row.get("asset_class")): asset_key(row.get("asset_class")) for rows in views.values() for row in rows}
    def root(key):
        while parent[key] != key:
            key = parent[key]
        return key
    def join(a, b):
        if a in parent and b in parent:
            left, right = sorted((root(a), root(b)))
            parent[right] = left
    for rows in views.values():
        for row in rows:
            for alias in row.get("aliases") or []:
                join(asset_key(row["asset_class"]), asset_key(alias))
    for proposal in (ideal, current):
        for view, rows in views.items():
            links, _ = reference_links(proposal, view, rows)
            for target, relations in links.items():
                for link in relations:
                    if link.get("relationship") == "equivalent":
                        join(target, link["source_key"])
    return {key: root(key) for key in parent}
