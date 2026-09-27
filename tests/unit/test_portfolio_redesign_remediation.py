"""Acceptance coverage for the second-pass request and recovery redesign."""

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

import pytest

from backend.portfolio_evidence import validate_stage
from backend.portfolio_independent import materialize_decision_records, apply_final_update
from backend.portfolio_recovery import field_repair_prompt, apply_row_repairs, parse_json_object
from backend.portfolio_requests import observation_brief, expand_observations, evidence_for_revision, payload_accounting
from backend.portfolio_runtime import PortfolioRuntime
from backend.portfolio_research import measurement_bindings, measurement_registry, reuse_measurements, deduplicate_measurement_searches, remaining_search


def ledger():
    return {"facts": [{"id": "inventory", "value": 2700, "metric": "commercial inventories", "unit": "million barrels",
        "benchmark": "OECD", "source_ids": ["s"], "source_excerpt": "OECD inventories were 2700 million barrels in August.",
        "observed_at": "2026-08-31"}], "source_packet": {"sources": [{"id": "s", "url": "https://example.test/inventory"}]},
        "fact_aliases": {"old": "inventory"}, "research_questions": []}


def question(identifier="q", dimension="August inventory", horizon="0-6 months", period="2026-08", answered=True):
    return {"id": identifier, "question": "What are inventories and the outlook?", "required_dimensions": [dimension],
        "asset_classes": ["oil"], "horizon": horizon, "searched_dimensions": [dimension],
        "dimension_measurements": [{"dimension": dimension, "scope": {"subject": "oil", "measure": "commercial inventories",
            "geography": "OECD", "period": period, "basis": "observed month end", "unit": "million barrels",
            "instrument": "physical stock", "vintage": "2026-09-12"}}],
        "answers": [{"dimension": dimension, "status": "answered" if answered else "unresolved",
            "answer": "Inventories 2700" if answered else "Not reported", "fact_ids": ["inventory"] if answered else []}]}


def test_observation_table_preserves_values_passages_aliases_and_checks():
    raw = ledger()
    raw["facts"].append({**raw["facts"][0], "id": "another", "value": 2600})
    packet = observation_brief(raw)
    expanded = expand_observations(packet)
    assert len(packet["source_passages"]) == 1
    assert [row["value"] for row in expanded["facts"]] == [2700, 2600]
    assert all(row["source_excerpt"] == raw["facts"][0]["source_excerpt"] for row in expanded["facts"])
    assert expanded["fact_aliases"] == raw["fact_aliases"]
    assert observation_brief(packet) == packet
    assert len(payload_accounting({"evidence_brief": packet})["evidence_packets"]["evidence_brief"]["fact_ids"]) == 2


def test_single_case_correction_excludes_other_cases_but_keeps_counterpart():
    raw = ledger()
    raw["facts"] += [{"id": "cash", "metric": "cash yield", "value": 4}, {"id": "copper", "metric": "copper price", "value": 5}]
    final = {"asset_class_targets": [{"asset_class": name, "fact_ids": [ref]} for name, ref in
        (("oil", "inventory"), ("cash", "cash"), ("copper", "copper"))]}
    packet = evidence_for_revision(raw, final, {"asset_classes": ["oil"], "funding_asset_classes": ["cash"]}, {})
    assert {row["id"] for row in packet["facts"]} == {"inventory", "cash"}


def test_shared_measurement_reused_across_different_question_horizons():
    raw = ledger()
    raw["research_questions"] = [question()]
    current = question("current", "Reported OECD stock", "3-12 months")
    current.update(answers=[], searched_dimensions=[])
    reused = reuse_measurements(current, raw)
    assert reused["status"] == "answered" and remaining_search(reused) is None
    assert reused["id"] != raw["research_questions"][0]["id"]
    assert len(measurement_registry({**raw, "research_questions": [*raw["research_questions"], reused]})) == 1


@pytest.mark.parametrize("field,value", [("period", "2027-08"), ("geography", "US"), ("basis", "forecast"),
    ("unit", "barrels"), ("instrument", "futures"), ("vintage", "2026-09-19")])
def test_different_measurement_scope_is_not_reused(field, value):
    raw = ledger()
    raw["research_questions"] = [question()]
    incoming = question("new")
    incoming.update(answers=[], searched_dimensions=[])
    incoming["dimension_measurements"][0]["scope"][field] = value
    incoming["dimension_measurements"][0]["reuse_measurement_id"] = next(iter(measurement_registry(raw)))
    result = reuse_measurements(incoming, raw)
    assert result["status"] == "unanswered" and not result["reused_measurement_ids"]
    assert remaining_search(result)


def test_unavailable_measurement_is_not_bought_again_at_same_cutoff():
    raw = ledger()
    raw["research_questions"] = [question(answered=False)]
    incoming = question("new", horizon="next year", answered=False)
    incoming["searched_dimensions"] = []
    result = reuse_measurements(incoming, raw)
    assert result["status"] == "unanswered" and remaining_search(result) is None


def test_independent_search_wave_buys_shared_dimension_once():
    first = question("first")
    second = question("second", "same stock", horizon="next year")
    third = question("third", "2027 stock", period="2027-08")
    searches = deduplicate_measurement_searches([first, second, third])
    assert [row["id"] for row in searches] == ["first", "third"]
    assert measurement_bindings(first)["august inventory"]["id"] == measurement_bindings(second)["same stock"]["id"]


@pytest.mark.asyncio
async def test_scheduler_distributes_shared_measurement_then_reuses_after_resume(tmp_path, monkeypatch):
    from unittest.mock import AsyncMock
    from backend.portfolio_runtime import CURRENT_RUNTIME
    from scripts import portfolio_positioning_memo as memo
    gather = AsyncMock(return_value={"results": [{"url": "https://example.test/inventory", "content": "Saved inventory report"}]})
    monkeypatch.setattr(memo.ParallelSourceProvider, "gather", gather)
    async def structure(lane, **kwargs):
        lane["evidence_brief"] = {**ledger(), "question_answers": [{"dimension": dimension, "status": "answered",
            "answer": "2700 million barrels", "fact_ids": ["inventory"]} for dimension in lane["question"]["required_dimensions"]]}
        return lane
    monkeypatch.setattr(memo, "_structure_evidence_lane", structure)
    rows = [question("a", "August stock", horizon="0-6 months"), question("b", "OECD inventory", horizon="3-12 months"),
        question("c", "Commercial stock", horizon="2-4 quarters")]
    for row in rows:
        row.update(material_reason="Inventory affects scarcity", reuse_assessment="Establish the reported level",
            period="August 2026", geography="OECD", economic_question=row["id"], answers=[], searched_dimensions=[])
    runtime = PortfolioRuntime(tmp_path / "measurements.json")
    token = CURRENT_RUNTIME.set(runtime)
    try:
        combined, runs, report = await memo._run_question_research(ledger(), "deep", {"phase": "independent", "questions": rows})
        assert gather.await_count == len(runs) == 1
        assert report["answered"] == 3
    finally:
        CURRENT_RUNTIME.reset(token)
    resumed = PortfolioRuntime(tmp_path / "resumed.json", runtime.checkpoint)
    token = CURRENT_RUNTIME.set(resumed)
    try:
        _, runs, report = await memo._run_question_research(combined, "deep", {"phase": "current", "questions": rows})
        assert not runs and report["answered"] == 3 and gather.await_count == 1
    finally:
        CURRENT_RUNTIME.reset(token)


def test_row_repair_keeps_valid_prose_and_rows_out_of_request():
    value = {"asset_class_targets": [{"asset_class": "oil", "min_pct": 0, "target_pct": 10, "max_pct": 20,
        "rationale": ["bad shape"], "fact_ids": ["inventory"]}, {"asset_class": "cash", "min_pct": 80,
        "target_pct": 90, "max_pct": 100, "rationale": "Valid argument " * 5000}]}
    prompt = {"required_schema": {"asset_class_targets": [{"asset_class": "string", "min_pct": "number",
        "target_pct": "number", "max_pct": "number", "rationale": "string", "fact_ids": ["id"]}]}, "evidence_brief": ledger()}
    errors = validate_stage(value, prompt)
    repair = field_repair_prompt(prompt, value, errors)
    assert [row["path"] for row in repair["allowed_repairs"]] == [["asset_class_targets", 0, "rationale"]]
    assert "Valid argument" not in json.dumps(repair)
    assert sum(row["target_pct"] for row in repair["recorded_allocation"]) == 100
    fixed = apply_row_repairs(value, {"patches": [{"path": ["asset_class_targets", 0, "rationale"],
        "value_json": '"Inventory supports the case"'}]}, repair)
    assert not validate_stage(fixed, prompt)
    assert fixed["asset_class_targets"][1] == value["asset_class_targets"][1]
    with pytest.raises(ValueError, match="unassigned"):
        apply_row_repairs(value, {"patches": [{"path": ["asset_class_targets", 1, "target_pct"], "value_json": "0"}]}, repair)


@pytest.mark.asyncio
async def test_runtime_merges_row_patch_and_records_actual_dispatch_size(tmp_path):
    prompt = {"task": "Test", "required_schema": {"rows": [{"argument": "string"}]}}
    calls = []
    async def client(model, messages, **kwargs):
        calls.append(json.loads(messages[0]["content"]))
        response = {"rows": [{"argument": ["wrong"]}, {"argument": "saved " * 5000}]} if len(calls) == 1 else {
            "patches": [{"path": ["rows", 0, "argument"], "value_json": '"fixed"'}]}
        return {"content": json.dumps(response)}
    runtime = PortfolioRuntime(tmp_path / "patch.json")
    result = await runtime.query(client, "model", [{"role": "user", "content": json.dumps(prompt)}],
        parser=parse_json_object, validator=validate_stage)
    assert result["stage_status"] == "complete" and len(calls) == 2
    assert json.loads(result["content"])["rows"][1]["argument"] == "saved " * 5000
    assert runtime.receipts[1]["payload_accounting"]["fields"].get("allowed_repairs")


def test_grouped_dispositions_expand_and_delta_retains_unchanged_rows():
    proposal = materialize_decision_records({"asset_class_targets": [{"asset_class": "cash", "min_pct": 0,
        "target_pct": 100, "max_pct": 100, "rationale": "Liquidity"}],
        "finding_resolutions": [{"finding_ids": ["a", "b"], "status": "accepted", "reason": "Corrected", "fact_ids": ["f"]}]})
    assert {row["finding_id"] for row in proposal["review_dispositions"]} == {"a", "b"}
    updated = apply_final_update(proposal, {"stage_status": "complete", "target_updates": [], "removed_target_ids": [],
        "updates": {"finding_resolutions": [{"finding_ids": ["a"], "status": "rebutted", "reason": "Source distinction", "fact_ids": ["f"]}]}})
    assert updated["final_reconciliation"]["status"] == "applied"
    assert {row["finding_id"]: row["status"] for row in updated["review_dispositions"]} == {"a": "rebutted", "b": "accepted"}
    assert updated["asset_class_targets"] == proposal["asset_class_targets"]


@pytest.mark.asyncio
async def test_stream_journal_flushes_during_silence(tmp_path, monkeypatch):
    from backend import portfolio_runtime as module
    monkeypatch.setattr(module, "STREAM_FLUSH_SECONDS", .01)
    observed = []
    async def client(model, messages, on_progress, **kwargs):
        await on_progress({"id": "request", "content_delta": "first"})
        await on_progress({"content_delta": "second"})
        await asyncio.sleep(.05)
        observed.append(next((tmp_path / ".portfolio-streams").glob("*.jsonl")).read_text())
        return {"content": '{"answer":"complete"}', "finish_reason": "stop"}
    client.supports_progress = True
    runtime = PortfolioRuntime(tmp_path / "journal.json")
    await runtime.query(client, "model", [{"role": "user", "content": '{"task":"Test","required_schema":{"answer":"string"}}'}],
        parser=parse_json_object, validator=validate_stage)
    assert "second" in observed[0]


def test_long_call_warning_is_observational_not_a_cancellation():
    from backend.portfolio_progress import PortfolioProgress
    progress = PortfolioProgress()
    identifier = progress.register("id", "analysis", "Analysis", "model")
    stamp = (datetime.now(timezone.utc) - timedelta(minutes=12)).isoformat()
    progress.update(identifier, status="running", started_at=stamp)
    snapshot = progress.snapshot()
    assert snapshot["active_requests"][0]["duration_warning"]
    assert progress.tasks[identifier]["status"] == "running"
