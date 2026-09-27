"""Render the saved analytical content without substituting diagnostic checklists."""

import re

from .portfolio_decisions import asset_key, number


def text(value):
    if value is None:
        return ""
    if isinstance(value, dict):
        return "; ".join(text(item) if key in {"key_messages", "notes", "summary", "rationale", "why_now"} else
                         f"{str(key).replace('_', ' ').capitalize()}: {text(item)}" for key, item in value.items()
                         if key not in {"fact_ids", "source_ids", "id", "stage_status", "model", "request_hash", "output_hash"} and text(item))
    if isinstance(value, list):
        return "; ".join(text(item) for item in value if text(item))
    return str(value).strip()


def pct(value):
    value = number(value)
    return "Not specified" if value is None else f"{value:g}%"


def label(row):
    return str(row.get("display_name") or row.get("asset_class") or "Exposure").replace("_", " ")


def play_rating(row):
    score = number(row.get("score"))
    if score is not None:
        qualifier = " (provisional)" if row.get("assessment_status") == "provisional" else ""
        return f"{score:g}/10{qualifier}"
    retained = number((row.get("reported_judgment") or {}).get("score"))
    return f"Provisional model view: {retained:g}/10; research incomplete" if retained is not None else "Not yet assessed"


def render_portfolio_memo(*, snapshot, structured, evidence_brief, citations):
    if structured.get("workflow_version", 0) >= 4:
        return render_research_led_memo(snapshot=snapshot, structured=structured, evidence=evidence_brief, citations=citations)
    lines = ["# Portfolio Positioning Memo"]

    def section(title, content):
        if content:
            lines.extend(["", "## " + title, "", *content])

    def bullets(values):
        return ["- " + text(value) for value in values or [] if text(value)]

    def table(rows, *, current=False):
        head = "| Exposure | Current | Range | Reference | Stance | Conviction |" if current else "| Exposure | Range | Reference | Conviction |"
        result = [head, "| --- | ---: | ---: | ---: | --- | --- |" if current else "| --- | ---: | ---: | --- |"]
        for row in rows or []:
            cells = [label(row)]
            if current:
                cells.append(pct(row.get("current_pct")))
            cells.extend([f"{pct(row.get('min_pct'))} - {pct(row.get('max_pct'))}", pct(row.get("target_pct"))])
            if current:
                cells.append(text(row.get("positioning_stance") or row.get("action") or "REVIEW"))
            cells.append(text(row.get("thesis_conviction") or row.get("conviction") or "Not assessed"))
            result.append("| " + " | ".join(cell.replace("|", "/").replace("\n", " ") for cell in cells) + " |")
        return result

    section("Executive View", [structured["executive_summary"]] if structured.get("executive_summary") else [])
    strategic = structured.get("strategic_view") or {}
    market = evidence_brief.get("market_view") or structured.get("market_view") or {}
    macro = evidence_brief.get("macro_scorecard") or structured.get("macro_scorecard") or {}
    quadrant = evidence_brief.get("quadrant_assessment") or structured.get("quadrant_assessment") or {}
    section("Market And Regime Assessment", [text(item) for item in [
        market, macro, quadrant.get("why_now"), strategic.get("primary_theme"), strategic.get("secondary_theme")]
        if text(item)] + bullets(strategic.get("notes")))
    section("Commodity Context", bullets(evidence_brief.get("commodity_prices")))
    section("Research Themes", bullets(evidence_brief.get("broker_themes")))

    ideal = structured.get("independent_ideal") or {}
    if ideal:
        content = [text(ideal.get("executive_summary"))]
        if ideal.get("asset_class_targets"):
            content += ["", *table(ideal["asset_class_targets"]), ""]
            content += [f"- **{label(row)}:** {text(row.get('rationale'))}" for row in ideal["asset_class_targets"]]
        section("Independent Ideal Portfolio", [item for item in content if item is not None])
        section("Opportunities Not Selected", bullets(ideal.get("excluded_opportunities")))

    assessment = structured.get("current_portfolio_assessment") or {}
    current_rows = assessment.get("current_assessment") or structured.get("current_sleeve_decisions") or []
    current_content = [text(assessment.get("executive_summary"))] if assessment.get("executive_summary") else []
    if assessment.get("asset_class_targets"):
        current_content.append("")
        current_content.append("**Current-aware alternative:** " + "; ".join(
            f"{label(row)} {pct(row.get('target_pct'))}" for row in assessment["asset_class_targets"]) + ".")
    current_content += [f"- **{label(row)} - {row.get('action') or 'REVIEW'}:** {text(row.get('allocator_commentary') or row.get('rationale'))}" for row in current_rows]
    section("Assessment Of Your Portfolio", current_content)

    plays = structured.get("play_assessments") or []
    play_content = []
    for play in plays:
        score = play.get("score")
        verdict = str(play.get("verdict") or "needs_research").replace("_", " ").capitalize()
        play_content.extend([f"### {play.get('title') or play.get('play_id')}", "",
            f"**Investment case: {score}/10. {verdict}.**" if score is not None else f"**Investment case: Not yet assessed. {verdict}.**",
            "", text(play.get("reason")), text(play.get("mechanism")), text(play.get("pricing")), text(play.get("portfolio_fit")),
            *bullets(play.get("contrary_evidence")), ""])
        if play.get("allocation_effect") or play.get("portfolio_action"):
            play_content.append("**Portfolio decision:** " + text(play.get("allocation_effect") or play["portfolio_action"]))
        if play.get("adopted_allocations"):
            play_content.append("**Included in the final allocation:** " + "; ".join(
                f"{label(row)} {pct(row.get('target_pct'))}" for row in play["adopted_allocations"]) + ".")
        if play.get("confidence"):
            play_content.append("**Evidence confidence:** " + text(play["confidence"]))
        if play.get("coverage_status") == "incomplete":
            play_content.append("Parts of this idea remain unassessed; the conclusions below do not cover the entire play.")
        for leg in play.get("legs") or []:
            rating = f"{leg['score']}/10" if leg.get("score") is not None else "Not yet assessed"
            play_content.extend(["", f"**{text(leg.get('name'))} - {rating}**",
                text(leg.get("mechanism")), text(leg.get("pricing")), text(leg.get("portfolio_action")),
                *bullets(leg.get("contrary_evidence"))])
            if leg.get("unanswered_question"):
                play_content.append("Still to establish: " + text(leg["unanswered_question"]))
        play_content.extend(bullets(play.get("expressions")))
        for review in structured.get("analytical_reviews") or []:
            if review.get("stage_status") == "failed":
                continue
            opinion = next((row for row in review.get("play_assessments") or [] if row.get("play_id") == play.get("play_id")), None)
            if opinion and (opinion.get("score"), opinion.get("verdict")) != (score, play.get("verdict")):
                role = "Exposure review" if review.get("council_lane") == "exposure_equivalence_reviewer" else "Defensive review"
                rating = f"{opinion['score']}/10" if opinion.get("score") is not None else "not yet assessed"
                play_content.append(f"**{role}: {rating}, {str(opinion.get('verdict') or 'needs research').replace('_', ' ')}.** {text(opinion.get('reason'))}")
    section("Investment Plays", [item for item in play_content if item is not None])

    targets = structured.get("asset_class_targets") or []
    if targets:
        content = table(targets, current=True)
        content += ["", *[f"- **{label(row)}:** {text(row.get('rationale'))}" for row in targets if row.get("rationale")]]
        section("Recommended Portfolio", content)
    commentary = structured.get("allocator_commentary") or {}
    reconciliation = structured.get("reconciliation") or []
    section("Reconciling The Two Views", ([text(commentary["comparison_summary"])] if commentary.get("comparison_summary") else []) +
            [f"- **{label(row)}:** {text(row.get('decision'))} {text(row.get('reason_for_departure'))}" for row in reconciliation] +
            bullets(commentary.get("portfolio_level_comments")))
    section("Allocator Commentary", [f"- **{label(row)}:** {text(row.get('commentary'))}" for row in commentary.get("asset_class_comments") or []])
    choice = structured.get("implementation_choice") or {}
    comparison = structured.get("implementation_comparison") or {}
    implementation_notes = bullets(structured.get("implementation_notes"))
    for key, title in (("hold_case", "Holding the current portfolio"), ("smaller_change_case", "Alternative considered" if comparison.get("issues") else "A smaller adjustment"),
                       ("chosen_case", "Changes justified now"), ("cost_assumptions", "Costs and constraints")):
        if choice.get(key):
            implementation_notes.append(f"**{title}:** {text(choice[key])}")
    smaller = (comparison.get("smaller_change") or {}).get("funding") or {}
    destination = (comparison.get("destination") or {}).get("funding") or {}
    if destination.get("one_way_turnover_pct") is not None:
        turnover = f"Reference allocation turnover: {pct(destination['one_way_turnover_pct'])}."
        if smaller.get("one_way_turnover_pct") is not None:
            name = "Alternative" if comparison.get("issues") else "Smaller-change alternative"
            turnover += f" {name}: {pct(smaller['one_way_turnover_pct'])}."
        implementation_notes.append(turnover)
    implementation_notes.extend(bullets(choice.get("conditions")))
    section("Implementation And Alternatives", implementation_notes)
    details = structured.get("investment_details") or {}
    detail_rows = details.get("asset_class_targets") or []
    implementation = []
    for row in detail_rows:
        case = row.get("investment_case") or {}
        relevant = [case.get("why_better_than_hold"), case.get("why_better_than_cash"), case.get("downside")]
        content = "; ".join(text(item) for item in relevant if text(item))
        if content:
            implementation.append(f"- **{label(row)}:** {content}")
        for alternative in row.get("alternatives") or []:
            if isinstance(alternative, dict) and alternative.get("name") and alternative.get("why_preferred"):
                implementation.append(f"  - **{text(alternative['name'])}:** {text(alternative['why_preferred'])}")
        execution = row.get("implementation") or {}
        if execution.get("instrument_type"):
            implementation.append(f"  - Proposed expression: {text(execution)}.")
    section("Investment Cases", implementation)
    section("Monitoring Triggers", bullets(structured.get("monitoring_triggers")))
    section("Forecasts And Conditions", bullets(structured.get("forecasts")))
    section("Risks And Uncertainties", bullets(structured.get("risk_flags")))

    # Claim-linked sources first, then any remaining cited references. Technical reviews stay in the appendix.
    sources = (evidence_brief.get("source_packet") or {}).get("sources") or citations or []
    by_id = {row.get("id"): row for row in sources}
    used = {ref for row in targets for ref in row.get("fact_ids", [])}
    linked = []
    for fact in evidence_brief.get("facts", []):
        if fact.get("id") in used:
            for ref in fact.get("source_ids", []):
                source = by_id.get(ref)
                if source:
                    linked.append(source)
    seen, source_lines = set(), []
    for source in linked + sources:
        url = source.get("url")
        if url and url not in seen:
            seen.add(url)
            source_lines.append(f"- [{source.get('title') or url}]({url})")
    section("Sources", source_lines)
    return "\n".join(lines).strip() + "\n"


def render_research_led_memo(*, snapshot, structured, evidence, citations):
    """Publish settled decisions first; preserve competing views and source detail in an appendix."""
    lines = ["# Portfolio Positioning Memo"]
    sources = (evidence.get("source_packet") or {}).get("sources") or citations or []
    source_by_id = {row.get("id"): row for row in sources}
    fact_links = {row["id"]: next((source_by_id[ref].get("url") for ref in row.get("source_ids", []) if ref in source_by_id), None)
                  for row in evidence.get("facts", []) if row.get("id")}

    def prose(value):
        raw = str(value or "").strip()
        raw = re.sub(r"\bquestion_[a-f0-9]{16,64}(?:(?:,\s*(?:and\s+)?|\s+and\s+)question_[a-f0-9]{16,64})+\b",
                     "the outstanding research questions", raw)
        raw = re.sub(r"\bquestion_[a-f0-9]{16,64}\b", "the outstanding research question", raw)
        raw = re.sub(r"\bfinding_[a-zA-Z0-9_-]+\b", "the review finding", raw)
        return re.sub(r"\bfact_[a-f0-9]{16,64}\b", lambda match:
            f"[source]({fact_links[match[0]]})" if fact_links.get(match[0]) else "source unavailable", raw)

    def paragraphs(value):
        if isinstance(value, dict):
            return [part for field, item in value.items() if field not in {
                "id", "fact_ids", "source_ids", "stage_status", "model", "request_hash", "output_hash", "checks"}
                for part in paragraphs(item)]
        if isinstance(value, list):
            return [part for item in value for part in paragraphs(item)]
        if value is None or value == "":
            return []
        return [prose(value)]  # Markdown already carries paragraphs, lists and tables.

    def emit(value):
        for paragraph in paragraphs(value):
            lines.extend([paragraph, ""])

    def cite(fact_ids):
        urls = list(dict.fromkeys(fact_links[ref] for ref in fact_ids or [] if fact_links.get(ref)))
        if urls:
            lines.extend([" ".join(f"[Source {index + 1}]({url})" for index, url in enumerate(urls)), ""])

    def section(title):
        lines.extend(["", "## " + title, ""])

    def weight(value):
        value = number(value)
        return "Not specified" if value is None else f"{value:.2f}".rstrip("0").rstrip(".") + "%"

    def cell(value):
        return prose(value).replace("|", "/").replace("\n", " ")

    targets = structured.get("asset_class_targets") or []
    ideal = structured.get("independent_ideal") or {}
    assessment = structured.get("current_portfolio_assessment") or {}
    if targets:
        section("Executive View")
        emit(structured.get("executive_summary"))
        emit((structured.get("strategic_view") or {}).get("theme_explanation"))
    else:
        section("Saved Draft Portfolios")
        emit(structured.get("partial_status") or "The final recommendation is not yet available. These are the saved proposals, before reconciliation.")
        for title, proposal in (("Independent Ideal Portfolio", ideal), ("Assessment Of Your Portfolio", assessment)):
            if not proposal.get("executive_summary") and not proposal.get("asset_class_targets"):
                continue
            section(title)
            emit(proposal.get("executive_summary"))
            rows = proposal.get("asset_class_targets") or []
            if rows:
                lines.extend(["| Exposure | Draft weight |", "| --- | ---: |"])
                for row in rows:
                    lines.append(f"| {cell(label(row))} | {weight(row.get('target_pct'))} |")
                lines.append("")
                for row in rows:
                    if row.get("rationale"):
                        emit(f"**{label(row)}.** {prose(row['rationale'])}")
                        cite(row.get("fact_ids"))
    reference = {asset_key(row.get("asset_class")): row.get("target_pct") for row in ideal.get("asset_class_targets", [])}
    reconciled = {asset_key(row.get("asset_class")): row for row in structured.get("reconciliation", [])}
    current = {asset_key(row.get("asset_class")): row.get("portfolio_pct") for row in snapshot.get("asset_classes", [])}
    current.setdefault("CASH", (snapshot.get("portfolio") or {}).get("cash_pct"))
    if targets:
        section("Recommended Portfolio")
        lines.extend(["| Exposure | Current | Independent ideal | Proposed |", "| --- | ---: | ---: | ---: |"])
        for row in targets:
            identifier = asset_key(row.get("asset_class"))
            baseline = reconciled.get(identifier, {}).get("ideal_reference_pct", reference.get(identifier))
            baseline_label = weight(baseline) if baseline is not None else "Not directly comparable"
            lines.append("| " + " | ".join((cell(label(row)), weight(row.get("current_pct", current.get(identifier))), baseline_label, weight(row.get("target_pct")))) + " |")
        section("Investment Case")
        for row in targets:
            if not row.get("rationale") and not row.get("investment_case_summary"):
                continue
            lines.extend(["### " + label(row), ""])
            emit(row.get("rationale") or row.get("investment_case_summary"))
            cite(row.get("fact_ids"))

    commentary = structured.get("allocator_commentary") or {}
    if commentary.get("comparison_summary") or commentary.get("portfolio_level_comments"):
        section("Reconciling The Two Views")
        emit(commentary.get("comparison_summary"))
        emit(commentary.get("portfolio_level_comments"))

    detailed_plays = [play for play in structured.get("play_assessments", []) if play.get("assessment_mode") != "brief"]
    if detailed_plays:
        section("Investment Plays")
    for play in detailed_plays:
        lines.extend(["### " + cell(play.get("title") or "Investment idea"), ""])
        emit(play.get("reason"))
        for leg in play.get("legs", []):
            score = play_rating(leg)
            lines.extend([f"**{cell(leg.get('name'))} - {score}**", ""])
            emit(leg.get("merit_reason") or leg.get("mechanism"))
            emit(leg.get("pricing"))
            if leg.get("confidence"):
                emit("Evidence confidence: " + str(leg["confidence"]).capitalize() + ".")
            if leg.get("portfolio_fit"):
                emit("Portfolio fit: " + prose(leg["portfolio_fit"]))
            if leg.get("portfolio_action"):
                emit("Portfolio decision: " + prose(leg["portfolio_action"]))
            for contrary in leg.get("contrary_evidence", []):
                lines.append("- " + cell(contrary))
            cite(leg.get("fact_ids"))
        if not play.get("legs"):
            emit("This idea has not yet received a component-by-component assessment.")
        emit(play.get("allocation_effect"))

    comparison = structured.get("implementation_comparison") or {}
    choice = structured.get("implementation_choice") or comparison.get("choice") or {}
    if choice or structured.get("implementation_notes") or (comparison.get("smaller_change") or {}).get("funding"):
        section("Implementation And Alternatives")
    for field, heading in (("hold_case", "Holding the current portfolio"), ("smaller_change_case", "A smaller adjustment"),
                           ("chosen_case", "Changes justified now"), ("cost_assumptions", "Costs and constraints")):
        if choice.get(field):
            lines.extend(["**" + heading + "**", ""])
            emit(choice[field])
    emit(structured.get("implementation_notes"))
    smaller = (comparison.get("smaller_change") or {}).get("funding") or {}
    if smaller.get("status") == "balanced":
        lines.extend(["| Smaller-change alternative | Weight |", "| --- | ---: |"])
        for row in smaller["rows"]:
            lines.append(f"| {cell(label(row))} | {weight(row['target_pct'])} |")
    elif smaller:
        emit("The smaller-change alternative is not fully funded and remains a proposal for review.")
    emit(choice.get("conditions"))
    if structured.get("monitoring_triggers"):
        section("Monitoring Triggers")
        for trigger in structured["monitoring_triggers"]:
            if isinstance(trigger, dict):
                emit("**" + cell(trigger.get("metric") or "Review condition") + "**")
                threshold = number(trigger.get("threshold"))
                if threshold is not None:
                    operator = {"gt": "above", "gte": "at or above", "lt": "below", "lte": "at or below"}.get(trigger.get("operator"), "at")
                    emit(f"{trigger.get('benchmark') or ''} {operator} {threshold:g} {trigger.get('unit') or ''}.")
                emit(trigger.get("what_changes"))
            else:
                emit(trigger)
    if structured.get("risk_flags"):
        section("Risks And Uncertainties")
        emit(structured["risk_flags"])

    brief_plays = [play for play in structured.get("play_assessments", []) if play.get("assessment_mode") == "brief"]
    if brief_plays:
        section("Investment Plays")
        for play in brief_plays:
            verdict = str(play.get("verdict") or "needs_research").replace("_", " ").capitalize()
            emit(f"**{cell(play.get('title') or 'Investment idea')} - {play_rating(play)} - {verdict}**")
            emit(play.get("reason"))
            action = play.get("allocation_effect") or play.get("portfolio_action")
            if action:
                emit(action)
            cite(play.get("fact_ids"))

    section("Supporting Research")
    if targets and ideal:
        lines.extend(["### Independent Ideal Portfolio", ""])
        emit(ideal.get("executive_summary"))
        for row in ideal.get("asset_class_targets", []):
            emit(f"**{label(row)}: {weight(row.get('target_pct'))}.** {prose(row.get('rationale'))}")
    if ideal.get("excluded_opportunities"):
        lines.extend(["### Opportunities Not Selected", ""])
        for row in ideal["excluded_opportunities"]:
            emit(f"**{cell(row.get('exposure'))}.** {prose(row.get('reason'))}" if isinstance(row, dict) else row)
    if targets and assessment:
        lines.extend(["### Assessment Of Your Portfolio", ""])
        emit(assessment.get("executive_summary"))
        for row in assessment.get("current_assessment", []):
            emit(f"**{label(row)}.** {prose(row.get('rationale') or row.get('allocator_commentary'))}")
    lines.extend(["### Market And Regime Assessment", ""])
    emit(evidence.get("market_view"))
    emit(evidence.get("macro_scorecard"))
    lines.extend(["### Research Questions", ""])
    from .portfolio_research import current_research_questions
    # Group presentation duplicates, preserving distinct regional/period answers together.
    questions = {}
    for question in current_research_questions(evidence):
        identity = " ".join(str(question.get("question") or "").casefold().split()).rstrip("?. ")
        questions.setdefault(identity, []).append(question)
    for group in questions.values():
        question = group[0]
        lines.extend(["**" + cell(question["question"]) + "**", ""])
        seen_answers = set()
        for question in group:
            if len(group) > 1:
                scope = " / ".join(dict.fromkeys(str(question[field]) for field in ("geography", "period", "horizon") if question.get(field)))
                if scope:
                    emit(scope)
            for answer in question.get("answers", []):
                identity = (str(answer.get("answer")), tuple(answer.get("fact_ids") or []))
                if identity not in seen_answers:
                    emit(answer.get("answer"))
                    cite(answer.get("fact_ids"))
                    seen_answers.add(identity)
            if question.get("status") != "answered":
                emit("Still unresolved: " + "; ".join(dict.fromkeys(question.get("missing_dimensions") or [question.get("reason") or "No sufficient source evidence returned."])))
    # Older artifacts can retain allocation gaps without the underlying question registry.
    known_ids = {row["id"] for row in evidence.get("research_questions", []) if row.get("id")}
    retained = {}
    for target in [*targets, *(leg for play in detailed_plays for leg in play.get("legs", []))]:
        gaps = [*target.get("research_gaps", [])]
        if target.get("unanswered_question"):
            gaps.append({"question": target["unanswered_question"]})
        for gap in gaps:
            identity = " ".join(str(gap.get("question") or "").casefold().split()).rstrip("?. ")
            if identity and identity not in questions and gap.get("question_id") not in known_ids and gap.get("status") not in {"answered", "not_market"}:
                retained.setdefault(identity, gap["question"])
    for question in retained.values():
        emit("**" + cell(question) + "**")
        emit("Recorded as unresolved in the saved analysis; no supporting answer record is available.")
    if any(row.get("investment_case") for row in targets):
        lines.extend(["### Detailed Investment Cases", ""])
    # These are the settled target cases, not archived pre-review drafts.
    for row in targets:
        case = row.get("investment_case") or {}
        if case:
            lines.extend(["#### " + label(row), ""])
            for field, title in (("why_better_than_hold", "Compared with holding"), ("why_better_than_cash", "Compared with cash"), ("downside", "Downside")):
                if case.get(field):
                    emit("**" + title + ".** " + prose(case[field]))
    if (structured.get("consistency_review") or {}).get("remaining_concerns"):
        lines.extend(["### Outstanding Review Questions", ""])
        emit(structured["consistency_review"]["remaining_concerns"])
    section("Sources")
    seen = set()
    for source in sources:
        if source.get("url") and source["url"] not in seen:
            seen.add(source["url"])
            lines.append(f"- [{cell(source.get('title') or source['url'])}]({source['url']})")
    return "\n".join(lines).strip() + "\n"
