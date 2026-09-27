"""Request scoping must reduce repetition without losing contrary evidence or provenance."""

from copy import deepcopy
import asyncio
import json
from unittest.mock import AsyncMock

import httpx
import pytest

from backend.portfolio_tasks import allocation_context, evidence_for_decisions, investment_details, investment_evidence
from backend.portfolio_decisions import funding_ledger
from backend.portfolio_independent import complete_play_assessments
from backend.portfolio_runtime import PortfolioRuntime
from backend.portfolio_evidence import validate_stage
from backend.portfolio_recovery import parse_json_object, recover_optional_fields


def ledger():
    facts = [{"id": name, "metric": metric, "benchmark": benchmark, "unit": "USD/t", "value": value,
              "observed_at": "2026-09-01", "source_ids": ["source"], "source_excerpt": f"{metric}: {value}",
              "claim_status": "supported", "claim_review": {"issues": [], "checks": {"value": "supported"}}}
             for name, metric, benchmark, value in (("margin", "Margin", "Fertiliser", 236),
                 ("contrary", "Cost", "Fertiliser", 216), ("prior", "Margin", "Fertiliser", 168),
                 ("oil", "Price", "Brent", 95))]
    return {"facts": facts, "source_packet": {"sources": [{"id": "source", "url": "https://example.test/report"}]},
            "market_view": {"fact_ids": ["oil"], "summary": "Global oil narrative"},
            "research_questions": [
                {"id": "fertiliser_case", "question": "What supports or challenges margins?", "asset_classes": ["fertiliser"],
                 "answers": [{"dimension": "economics", "answer": "Margins improved; costs remain a risk.", "fact_ids": ["margin", "contrary"]}],
                 "play_ids": ["scarcity"], "component_ids": ["fertiliser_leg"], "missing_dimensions": ["Valuation"]},
                {"id": "oil_case", "question": "What is the oil price?", "asset_classes": ["energy"],
                 "answers": [{"answer": "95", "fact_ids": ["oil"]}]}]}


def test_repeated_projection_preserves_sources_checks_questions_and_context():
    original = ledger()
    first = investment_evidence(original)
    second = investment_evidence(first)
    assert second == first
    assert second["sources"] and second["research_questions"] and second["initial_market_context"]
    assert second["facts"][0]["source_review"]["status"] == "supported"
    second["facts"][0]["value"] = 0
    assert first["facts"][0]["value"] == 236 and original["facts"][0]["value"] == 236
    legacy = deepcopy(first)
    legacy.pop("evidence_view")
    assert investment_evidence(legacy) == legacy


def test_scoped_cases_include_uncited_contrary_and_prior_observations_not_global_links():
    original = ledger()
    decision = [{"asset_class": "fertiliser", "fact_ids": ["margin"]}]
    for packet in (original, investment_evidence(original)):
        scoped = evidence_for_decisions(packet, decision)
        assert {fact["id"] for fact in scoped["facts"]} == {"margin", "contrary", "prior"}
        assert len(scoped["sources"]) == 1
        assert [row["question_id"] for row in scoped["research_questions"]] == ["fertiliser_case"]
        assert scoped["research_questions"][0]["missing_dimensions"] == ["Valuation"]
        assert "initial_market_context" not in scoped and "other_observations" not in scoped
        assert evidence_for_decisions(scoped, decision) == scoped


def test_new_exposure_can_follow_declared_question_id_without_name_matching():
    result = evidence_for_decisions(ledger(), [{"asset_class": "new_unrelated_display_name", "research_question_ids": ["fertiliser_case"]}])
    assert {row["id"] for row in result["facts"]} == {"margin", "contrary", "prior"}
    empty = evidence_for_decisions(ledger(), [{"asset_class": "not_researched"}])
    assert not empty["facts"] and empty["evidence_scope"]["available_facts"] == 4
    aliased = ledger()
    aliased["fact_aliases"] = {"old_margin_id": "margin"}
    projected = investment_evidence(aliased)
    assert "margin" in {row["id"] for row in evidence_for_decisions(projected, {"fact_ids": ["old_margin_id"]})["facts"]}


def test_detail_records_do_not_copy_proposal_or_change_it():
    proposal = {"executive_summary": "Essay", "play_assessments": [{"reason": "Another essay"}],
                "asset_class_targets": [{"asset_class": "cash", "target_pct": 100, "rationale": "Keep optionality",
                    "investment_case": {"why_better_than_hold": "No change"}, "detail_status": "current"}]}
    assert allocation_context(proposal) == [{"asset_class": "cash", "target_pct": 100}]
    details = investment_details(proposal)
    assert set(details) == {"asset_class_targets", "warnings"}
    assert "target_pct" not in details["asset_class_targets"][0]
    assert "investment_case" in details["asset_class_targets"][0]
    assert proposal["executive_summary"] == "Essay"


def test_stable_component_id_survives_display_name_variation():
    plays = [{"id": "p", "title": "Scarcity", "components": [{"id": "leg", "name": "Fertiliser producers", "source_text": "fertiliser"}]}]
    result = complete_play_assessments(plays, [{"play_id": "p", "score": 6, "verdict": "watch",
        "legs": [{"component_id": "leg", "name": "Agricultural inputs", "score": 6, "verdict": "watch", "mechanism": "Margins improved"}]}])
    assert result[0]["legs"][0]["score"] == 6
    assert result[0]["legs"][0]["name"] == "Fertiliser producers"
    assert result[0]["legs"][0]["reported_name"] == "Agricultural inputs"


def test_unverified_mapping_does_not_duplicate_final_capital():
    book = {"portfolio": {"cash_pct": 20}, "asset_classes": [{"asset_class": "pharma", "portfolio_pct": 80}]}
    proposal = {"asset_class_targets": [
        {"asset_class": "new_pharma", "min_pct": 40, "target_pct": 40, "max_pct": 40,
         "baseline_links": [{"view": "holdings", "asset_class": "pharma", "relationship": "equivalent"}]},
        {"asset_class": "cash", "min_pct": 60, "target_pct": 60, "max_pct": 60}],
        "current_sleeve_actions": [{"asset_class": "pharma", "action": "TRIM", "target_pct": 40}]}
    result = funding_ledger(book, proposal)
    assert result["specified_target_total_pct"] == 100
    assert result["status"] == "unresolved" and result["issues"]
    assert result["rows"][0]["current_pct"] is None
    assert result["unresolved_current_actions"][0]["target_pct"] == 40
    assert result["one_way_turnover_pct"] is None


def test_time_change_is_chronological_in_either_operand_order():
    from backend.portfolio_judgment import calculate_financial_claims
    old = {"id": "old", "metric": "Real yield", "benchmark": "US TIPS 10Y", "unit": "%", "currency": "USD",
           "observed_at": "2026-09-08", "value": 2.43, "measurement": {"price_basis": "real", "horizon_months": 120}}
    new = {**old, "id": "new", "value": 2.68, "observed_at": "2026-09-16"}
    for refs in (["old", "new"], ["new", "old"]):
        result = calculate_financial_claims({"calculations": [{"operation": "time_change", "fact_ids": refs}]}, {"facts": [old, new]})[0]
        assert result["computed_value"] == .25 and result["basis_points"] == 25
        assert result["calculation_order"] == {"from_fact_id": "old", "to_fact_id": "new"}


def test_question_identity_survives_topic_heading_and_dimension_paraphrase():
    from backend.portfolio_research import normalize_questions, matching_question, merge_question, remaining_search
    base = {"question": "What are inventory levels?", "topic": "Oil", "economic_question": "commercial_inventory",
        "geography": "OECD", "period": "August 2026", "horizon": "6 months", "asset_classes": ["energy"],
        "required_dimensions": ["days of cover"], "material_reason": "Physical supply", "reuse_assessment": "Missing latest release"}
    old = normalize_questions([base])[0]
    old["searched_dimensions"] = ["days of cover"]
    renamed = normalize_questions([{**base, "topic": "OECD commercial crude", "question": "How long do stocks last?",
        "required_dimensions": ["inventory coverage days"],
        "dimension_aliases": [{"dimension": "inventory coverage days", "existing_dimension": "days of cover"}]}])[0]
    assert renamed["id"] == old["id"]
    assert matching_question(renamed, {old["id"]: old}) == old
    merged = merge_question(old, renamed, {})
    assert remaining_search(merged) is None
    assert merged["question"] == old["question"] and renamed["question"] in merged["question_aliases"]
    other_period = normalize_questions([{**base, "period": "September 2026", "reuse_question_id": old["id"]}])[0]
    assert matching_question(other_period, {old["id"]: old}) is None


def test_final_delta_keeps_unchanged_analysis_and_does_not_materialise_nulls():
    from backend.portfolio_independent import apply_final_update, reconciliation_prompt
    base = {"executive_summary": "Original case", "asset_class_targets": [
        {"asset_class": "gold", "min_pct": 0, "target_pct": 20, "max_pct": 50},
        {"asset_class": "cash", "min_pct": 0, "target_pct": 80, "max_pct": 100}],
        "play_assessments": [{"play_id": "p", "score": 7, "reason": "Long-term hedge"}]}
    prompt = reconciliation_prompt({}, {"research_cutoff": "2026-09-20"}, {}, {}, {}, [], [], provisional=base)
    assert "100-150 words" in prompt["required_schema"]["updates"]["executive_summary"]
    assert "Include updates.executive_summary" in " ".join(prompt["rules"])
    response, _ = recover_optional_fields({"reason": "Reweight the hedge", "target_updates": [
        {"asset_class": "gold", "target_pct": 30}, {"asset_class": "cash", "target_pct": 70}], "updates": {}}, prompt)
    assert response["updates"] == {} and "executive_summary" not in response["updates"]
    final = apply_final_update(base, {**response, "stage_status": "complete"})
    assert final["final_reconciliation"]["status"] == "applied"
    assert final["executive_summary"] == base["executive_summary"]
    assert final["play_assessments"] == base["play_assessments"]
    assert final["asset_class_targets"][0]["target_pct"] == 30
    assert base["asset_class_targets"][0]["target_pct"] == 20
    broken = apply_final_update(base, {"stage_status": "complete", "target_updates": [{"asset_class": "gold", "target_pct": 40}]})
    assert broken["asset_class_targets"] == base["asset_class_targets"]
    assert broken["final_reconciliation"]["unapplied_candidate"]["asset_class_targets"][0]["target_pct"] == 40
    base["play_assessments"][0]["legs"] = [{"component_id": "gold", "score": 7}, {"component_id": "silver", "score": 5}]
    changed_play = apply_final_update(base, {"stage_status": "complete", "updates": {"play_assessments": [
        {"play_id": "p", "legs": [{"component_id": "gold", "score": 8}]}]}})
    assert changed_play["play_assessments"][0]["legs"] == [{"component_id": "gold", "score": 8}, {"component_id": "silver", "score": 5}]


def test_compact_details_still_reuse_unchanged_cases():
    from backend.portfolio_judgment import retain_current_details, detail_basis
    target = {"asset_class": "fertiliser", "target_pct": 5, "rationale": "Improved margins", "fact_ids": ["margin"],
              "investment_case": {"why_better_than_hold": "Improved margins"}, "detail_status": "current"}
    target["detail_evidence_hash"] = detail_basis(target, ledger())
    compact = investment_details({"asset_class_targets": [target]})
    final, stale = retain_current_details({"asset_class_targets": [{key: value for key, value in target.items()
        if key not in {"investment_case", "detail_status", "detail_evidence_hash"}}]}, compact, ledger())
    assert not stale and final["asset_class_targets"][0]["investment_case"] == target["investment_case"]


def test_json_repairs_never_guess_financial_values_or_choose_duplicate_keys():
    assert parse_json_object('```json\n{"value": -0.25, "notes": ["x,}",],}\n```') == {"value": -.25, "notes": ["x,}"]}
    assert parse_json_object('{"text":"line one\nline two"}') == {"text": "line one\nline two"}
    assert parse_json_object('{"value": 1, "value": 2}') is None
    assert parse_json_object('{"value":') is None


@pytest.mark.asyncio
async def test_source_extraction_reuses_identical_snapshots_across_groupings_and_resume(tmp_path):
    from backend.portfolio_tasks import cached_source_extraction
    runtime = PortfolioRuntime(tmp_path / "source.checkpoint.json")
    a = {"id": "a", "url": "https://example.test/a", "excerpt": "Price 20", "published_at": "2026-09-01"}
    b = {"id": "b", "url": "https://example.test/b", "excerpt": "Price 30", "published_at": "2026-09-02"}
    async def extract(sources):
        return {"stage_status": "complete", "content": json.dumps({"facts": [{"source_ids": [s["id"]], "source_excerpt": s["excerpt"]} for s in sources]})}
    call = AsyncMock(side_effect=extract)
    async def run(sources, instance=runtime):
        return await cached_source_extraction(instance, {"as_of": "2026-09-20", "sources": sources}, "model", {"version": 1}, call, parse_json_object)
    await asyncio.gather(run([a, b]), run([a]))
    assert call.await_count == 1
    resumed = PortfolioRuntime(tmp_path / "resumed.json", runtime.checkpoint)
    assert (await run([b], resumed))["source_cache_reused"] == 1
    assert call.await_count == 1
    await run([{**a, "excerpt": "Price 22"}], resumed)
    assert call.await_count == 2


@pytest.mark.asyncio
async def test_scoped_json_repair_keeps_valid_large_field_without_replaying_it():
    large = "Already saved financial argument. " * 5000
    messages = [{"role": "user", "content": json.dumps({"task": "Example", "required_schema": {"essay": "string", "answer": "string"}})}]
    client = AsyncMock(side_effect=[{"content": json.dumps({"essay": large})}, {"content": '{"answer":"fixed"}'}])
    result = await PortfolioRuntime().query(client, "model", messages, parser=parse_json_object, validator=validate_stage)
    assert json.loads(result["content"]) == {"essay": large, "answer": "fixed"}
    assert large not in json.dumps(client.call_args_list[1].args[1])


@pytest.mark.asyncio
async def test_streamed_output_is_journalled_and_uncertain_call_is_not_resubmitted(tmp_path, monkeypatch):
    from backend import openrouter
    original_client = httpx.AsyncClient
    class Interrupted(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'data: {"id":"paid-request", "choices":[{"index":0,"delta":{"content":"partial financial work"}}]}\n\n'
            raise httpx.ReadError("Connection lost")
    calls = []
    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, headers={"Content-Type": "text/event-stream"}, stream=Interrupted())
    monkeypatch.setattr(openrouter.httpx, "AsyncClient", lambda **kwargs: original_client(transport=httpx.MockTransport(respond), **kwargs))
    runtime = PortfolioRuntime(tmp_path / "stream.checkpoint.json")
    messages = [{"role": "user", "content": json.dumps({"task": "Example", "required_schema": {"answer": "string"}})}]
    result = await runtime.query(openrouter.query_model, "model", messages, parser=parse_json_object, validator=validate_stage)
    assert result["stage_status"] == "failed" and len(calls) == 1
    assert calls[0]["stream"] is True and "max_tokens" not in calls[0]
    assert "partial financial work" in next((tmp_path / ".portfolio-streams").glob("*.jsonl")).read_text()
    resumed = PortfolioRuntime(tmp_path / "resumed.checkpoint.json", runtime.checkpoint)
    result = await resumed.query(openrouter.query_model, "model", messages, parser=parse_json_object, validator=validate_stage)
    assert result["error_type"] == "provider_outcome_uncertain" and len(calls) == 1


@pytest.mark.asyncio
async def test_complete_stream_retains_finish_reason_usage_and_progress(tmp_path, monkeypatch):
    from backend import openrouter
    original_client = httpx.AsyncClient
    chunks = [{"id": "done", "model": "resolved/model", "choices": [{"index": 0, "delta": {"content": '{"answer":'}}]},
              {"choices": [{"index": 0, "delta": {"content": '"saved"}'}, "finish_reason": "stop"}]},
              {"choices": [], "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": .01}}]
    content = "".join("data: " + json.dumps(chunk) + "\n\n" for chunk in chunks) + "data: [DONE]\n\n"
    monkeypatch.setattr(openrouter.httpx, "AsyncClient", lambda **kwargs: original_client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, headers={"content-type": "text/event-stream"}, content=content)), **kwargs))
    runtime = PortfolioRuntime(tmp_path / "complete.json")
    result = await runtime.query(openrouter.query_model, "requested/model", [{"role": "user", "content": json.dumps(
        {"task": "Example", "required_schema": {"answer": "string"}})}], parser=parse_json_object, validator=validate_stage)
    assert result["stage_status"] == "complete" and result["resolved_model"] == "resolved/model"
    assert result["usage"]["completion_tokens"] == 5
    task = next(iter(runtime.progress.tasks.values()))
    assert task["received_characters"] == len('{"answer":"saved"}') and task["first_content_at"]


@pytest.mark.asyncio
async def test_native_truncation_retains_complete_allocation_without_paid_regeneration():
    prompt = {"task": "Portfolio", "contract": "independent-portfolio-v1", "required_schema": {
        "asset_class_targets": [{"asset_class": "id", "min_pct": "number", "target_pct": "number", "max_pct": "number"}],
        "risk_flags": ["risk"]}}
    text = '{"asset_class_targets":[{"asset_class":"cash","min_pct":100,"target_pct":100,"max_pct":100}],"risk_flags":["unfinished'
    client = AsyncMock(return_value={"content": text, "finish_reason": "length"})
    runtime = PortfolioRuntime()
    result = await runtime.query(client, "model", [{"role": "user", "content": json.dumps(prompt)}], parser=parse_json_object, validator=validate_stage)
    assert result["stage_status"] == "complete" and client.await_count == 1
    assert result["warnings"] and runtime.receipts[0]["provider_truncation_retained"]
    assert json.loads(result["content"])["asset_class_targets"][0]["target_pct"] == 100


@pytest.mark.asyncio
async def test_review_can_inspect_uncited_archive_evidence_without_another_search(tmp_path, monkeypatch):
    import backend.portfolio_independent as independent
    monkeypatch.setattr(independent, "review_prompt_batches", lambda *args: [{"task": "review", "evidence_brief": {"facts": []}}])
    call = AsyncMock(side_effect=[{"stage_status": "complete", "summary": "Inspect the oil quote",
        "findings": [], "evidence_requests": [{"fact_ids": ["oil"], "reason": "Price benchmark matters"}]},
        {"stage_status": "complete", "finding_updates": [{"finding_id": None, "asset_class": "energy", "argument": "The source specifies Brent",
            "kind": "factual_correction", "fact_ids": ["oil"]}], "play_updates": []}])
    result = await independent.run_financial_review("reviewer", "model", ledger(), {}, {}, {}, {}, [], call, PortfolioRuntime(tmp_path / "review.json"))
    assert call.await_count == 2 and result["findings"][0]["argument"] == "The source specifies Brent"
    packet = call.call_args_list[1].args[2]["evidence_brief"]
    assert [row["id"] for row in packet["facts"]] == ["oil"]
    assert packet["facts"][0]["source_excerpt"] == "Price: 95"


@pytest.mark.asyncio
async def test_review_parts_execute_independently_and_join_after_completion(tmp_path, monkeypatch):
    import backend.portfolio_independent as independent
    monkeypatch.setattr(independent, "review_prompt_batches", lambda *args: [{"task": "one"}, {"task": "two"}])
    started = set()
    both = asyncio.Event()
    async def call(role, model, prompt, **kwargs):
        started.add(prompt["task"])
        if len(started) == 2:
            both.set()
        await asyncio.wait_for(both.wait(), 1)
        return {"stage_status": "complete", "summary": prompt["task"], "findings": [{"argument": prompt["task"]}]}
    result = await independent.run_financial_review("reviewer", "model", {}, {}, {}, {}, {}, [], call, PortfolioRuntime(tmp_path / "parts.json"))
    assert [row["argument"] for row in result["findings"]] == ["one", "two"]


@pytest.mark.asyncio
async def test_focused_search_does_not_generate_another_global_macro_brief(monkeypatch):
    from scripts import portfolio_positioning_memo as memo
    prompts = []
    async def query(model, messages, **kwargs):
        prompt = json.loads(messages[0]["content"])
        prompts.append(prompt)
        if "facts" in prompt["required_schema"]:
            source = prompt["source_packet"]["sources"][0]
            fact = {**ledger()["facts"][0], "source_ids": [source["id"]], "source_excerpt": source["excerpt"]}
            return {"stage_status": "complete", "content": json.dumps({"facts": [fact]})}
        return {"stage_status": "complete", "content": json.dumps({"question_answers": [], "research_limitations": []})}
    monkeypatch.setattr(memo, "_query_stage", query)
    await memo._build_evidence_brief(query="Generic investment context", mode="deep", macro_news={},
        tavily_result={"provider": "parallel", "results": [{"url": "https://example.test/facts", "content": "Margin 236", "published_at": "2026-09-01"}]},
        perplexity_result={}, asset_class_vocabulary=[], research_question={"id": "margin", "question": "What is the margin?", "required_dimensions": ["margin"]})
    assert len(prompts) == 2
    assert set(prompts[1]["required_schema"]) == {"question_answers", "research_limitations",
        "source_urls_to_inspect", "followup_question", "followup_search_queries"}
    assert "macro_scorecard" not in prompts[1]["required_schema"]
    assert "user_query" not in prompts[0] and "lane_focus" not in prompts[0]
