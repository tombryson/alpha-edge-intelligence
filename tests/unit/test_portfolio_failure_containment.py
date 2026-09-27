import json
from copy import deepcopy
from unittest.mock import AsyncMock

import pytest

import portfolio_positioning_memo as memo
from backend.portfolio_decisions import analysis_health
from backend.portfolio_evidence import FACT_CHECK_SCHEMA, FACT_FIELDS, apply_fact_checks, fact_is_supported, validate_stage
from backend.portfolio_recovery import recover_optional_fields
from backend.portfolio_runtime import PortfolioRuntime


def review_prompt():
    return {"task": "Review source support / batch 17", "required_schema": {"fact_checks": FACT_CHECK_SCHEMA},
        "evidence": {"facts": [{"id": f"f{i}", "source_ids": [f"s{i}"]} for i in range(8)],
                     "source_packet": {"sources": [{"id": f"s{i}", "excerpt": f"Original source {i}"} for i in range(8)]}}}


def reviews():
    return {"fact_checks": [{"fact_id": f"f{i}", "checks": {key: "supported" for key in FACT_FIELDS},
                             "reason": f"Source explanation {i}"} for i in range(8)]}


async def query(runtime, client, prompt=None, **kwargs):
    return await runtime.query(client, "~deepseek/deepseek-flash-latest",
        [{"role": "user", "content": json.dumps(prompt or review_prompt())}],
        parser=memo._extract_json_object, validator=validate_stage, **kwargs)


@pytest.mark.asyncio
async def test_exact_failure_shape_gets_targeted_repair_then_local_unresolved():
    missing = reviews()
    del missing["fact_checks"][5]["checks"]["currency"]
    client = AsyncMock(side_effect=[
        {"content": "", "finish_reason": "length"},
        {"content": json.dumps(missing), "finish_reason": "stop"},
        {"content": json.dumps({"fact_checks": [missing["fact_checks"][5]]}), "finish_reason": "stop"},
    ])
    runtime = PortfolioRuntime()
    result = await query(runtime, client, max_tokens=12000)
    assert result["stage_status"] == "complete"
    rows = json.loads(result["content"])["fact_checks"]
    assert len(rows) == 8
    for index, row in enumerate(rows):
        assert row["reason"] == f"Source explanation {index}"
        assert row["checks"] == {key: "unresolved" if index == 5 and key == "currency" else "supported" for key in FACT_FIELDS}
    repair = json.loads(client.call_args.args[1][0]["content"])
    assert repair["repair_fields"] == {"f5": ["currency"]}
    assert [fact["id"] for fact in repair["evidence"]["facts"]] == ["f5"]
    assert [source["id"] for source in repair["evidence"]["source_packet"]["sources"]] == ["s5"]
    assert result["warnings"][0]["fields"] == ["currency"]
    assert runtime.receipts[-1]["status"] == "complete"
    assert runtime.receipts[-1]["completion_mode"] == "with_limitations"
    assert runtime.receipts[-2]["status"] == "failed"
    assert runtime.receipts[-2]["raw_response"]["content"]
    assert next(iter(runtime.cache.values()))["receipt"]["warnings"]


@pytest.mark.asyncio
async def test_targeted_repair_cannot_overwrite_other_accepted_verdicts():
    missing = reviews()
    del missing["fact_checks"][5]["checks"]["currency"]
    missing["fact_checks"][5]["checks"]["value"] = "unsupported"
    changed = reviews()
    changed["fact_checks"][0]["checks"]["value"] = "unsupported"
    client = AsyncMock(side_effect=[{"content": json.dumps(missing)}, {"content": json.dumps(changed)}])
    result = await query(PortfolioRuntime(), client)
    rows = json.loads(result["content"])["fact_checks"]
    assert result["stage_status"] == "complete" and not result["warnings"]
    assert rows[0]["checks"]["value"] == "supported"
    assert rows[5]["checks"]["value"] == "unsupported"
    assert rows[5]["checks"]["currency"] == "supported"


@pytest.mark.asyncio
@pytest.mark.parametrize("damage", ["missing_row", "duplicate", "bad_value", "missing_reason", "malformed"])
async def test_review_defects_are_contained_without_inventing_verification(damage):
    value = reviews()
    if damage == "missing_row":
        value["fact_checks"].pop(5)
    elif damage == "duplicate":
        value["fact_checks"].append(deepcopy(value["fact_checks"][5]))
    elif damage == "bad_value":
        value["fact_checks"][5]["checks"]["currency"] = {"guess": "supported"}
    elif damage == "missing_reason":
        value["fact_checks"][5].pop("reason")
    elif damage == "malformed":
        value = {"fact_checks": 123}
    result = await query(PortfolioRuntime(), AsyncMock(return_value={"content": json.dumps(value)}))
    assert result["stage_status"] == "complete"
    rows = json.loads(result["content"])["fact_checks"]
    assert rows[5]["checks"]["currency"] == "unresolved"
    if damage != "malformed":
        assert rows[0]["checks"]["currency"] == "supported"
    assert result["warnings"]


@pytest.mark.asyncio
async def test_unavailable_reviewer_is_not_a_total_loss_of_research():
    runtime = PortfolioRuntime()
    client = AsyncMock(return_value={"error": "No credits", "error_type": "http_error", "error_status": 402})
    result = await query(runtime, client)
    assert client.await_count == 1
    assert result["stage_status"] == "complete"
    assert all(set(row["checks"].values()) == {"unresolved"} for row in json.loads(result["content"])["fact_checks"])
    assert runtime.receipts[0]["error"] == "No credits"
    assert runtime.receipts[-1]["recovery_error"] == "No credits"


def test_unreviewed_currency_does_not_become_supported():
    fact = {"id": "f1", "kind": "market_price", "metric": "FX rate", "value": 96, "unit": "INR/USD",
            "currency": "INR", "benchmark": "USD/INR", "observed_at": "2026-09-16", "published_at": "2026-09-16",
            "vintage": "live", "source_ids": ["s1"], "source_excerpt": "USD/INR 96"}
    packet = {"as_of": "2026-09-16T11:05:24Z", "sources": [{"id": "s1", "excerpt": "USD/INR 96"}]}
    checks = {key: "unresolved" if key == "currency" else "supported" for key in FACT_FIELDS}
    result = apply_fact_checks([fact], [{"fact_id": "f1", "checks": checks, "reason": "Currency review omitted"}], packet)
    assert result[0]["claim_status"] == "unresolved"
    assert not fact_is_supported(result[0])


def test_investment_detail_recovery_never_changes_weights_or_adds_assets():
    prompt = {"required_schema": {"allocation_details": [{"asset_class": "id", "implementation": {"currency": "string"}}]},
              "assigned_allocations": [{"asset_class": "cash", "target_pct": 100}]}
    value = {"allocation_details": [{"asset_class": "cash", "target_pct": 0, "implementation": {}},
                                     {"asset_class": "invented", "target_pct": 100}]}
    recovered, warnings = recover_optional_fields(value, prompt)
    assert recovered == {"allocation_details": [{"asset_class": "cash", "implementation": {"currency": None}}]}
    assert warnings and not validate_stage(recovered, prompt)
    assert value["allocation_details"][0]["target_pct"] == 0


@pytest.mark.asyncio
async def test_missing_optional_allocation_section_does_not_erase_funded_proposal():
    proposal = {"asset_class_targets": [{"asset_class": "cash", "min_pct": 100, "target_pct": 100, "max_pct": 100}]}
    prompt = {"task": "Allocate", "required_schema": {"asset_class_targets": [{}], "confidence_note": "string", "monitoring_triggers": []}}
    client = AsyncMock(return_value={"content": json.dumps(proposal)})
    result = await query(PortfolioRuntime(), client, prompt)
    assert client.await_count == 1 and result["stage_status"] == "complete"
    assert json.loads(result["content"])["asset_class_targets"] == proposal["asset_class_targets"]
    assert result["warnings"]


@pytest.mark.asyncio
async def test_funding_failure_remains_blocking_but_retains_original_proposal():
    proposal = {"asset_class_targets": [{"asset_class": "cash", "min_pct": 90, "target_pct": 90, "max_pct": 90}]}
    prompt = {"task": "Allocate", "required_schema": {"asset_class_targets": [{}]}}
    result = await query(PortfolioRuntime(), AsyncMock(return_value={"content": json.dumps(proposal)}), prompt)
    assert result["stage_status"] == "failed"
    assert result["partial_proposal"] == proposal
    assert result["content"] == ""


@pytest.mark.asyncio
async def test_same_request_can_resume_across_code_change_after_revalidation(tmp_path):
    path = tmp_path / "old.checkpoint.json"
    old = PortfolioRuntime(path)
    old.code = {"old": "manifest"}
    await query(old, AsyncMock(return_value={"content": json.dumps(reviews())}))
    resumed = PortfolioRuntime(tmp_path / "new.checkpoint.json", path)
    unused = AsyncMock(side_effect=AssertionError("Must reuse completed review"))
    assert (await query(resumed, unused))["stage_status"] == "complete"
    assert resumed.receipts[0]["revalidated"]
    unused.assert_not_awaited()
    changed = review_prompt()
    changed["evidence"]["source_packet"]["sources"][0]["excerpt"] = "Changed source"
    client = AsyncMock(return_value={"content": json.dumps(reviews())})
    await query(resumed, client, changed)
    assert client.await_count == 1


@pytest.mark.asyncio
async def test_historical_failed_review_resumes_only_missing_field(tmp_path):
    path = tmp_path / "old.checkpoint.json"
    old = PortfolioRuntime(path)
    old.code = {"old": "manifest"}
    missing = reviews()
    del missing["fact_checks"][5]["checks"]["currency"]
    await query(old, AsyncMock(return_value={"content": json.dumps(missing)}))
    saved = json.loads(path.read_text())
    saved["stage_receipts"] = [r for r in saved["stage_receipts"] if r["status"] == "failed"]
    saved["stage_cache"] = {}
    path.write_text(json.dumps(saved))
    resumed = PortfolioRuntime(tmp_path / "new.checkpoint.json", path)
    client = AsyncMock(return_value={"content": json.dumps({"fact_checks": [{"fact_id": "f5", "checks": {"currency": "supported"}}]})})
    result = await query(resumed, client)
    assert result["stage_status"] == "complete" and not result["warnings"]
    assert client.await_count == 1
    repair = json.loads(client.call_args.args[1][0]["content"])
    assert repair["repair_fields"] == {"f5": ["currency"]}
    assert len(json.loads(result["content"])["fact_checks"]) == 8


@pytest.mark.asyncio
@pytest.mark.parametrize("legacy_missing_cache", [False, True])
async def test_repeated_resume_preserves_completed_reviews_and_warnings(tmp_path, legacy_missing_cache):
    path = tmp_path / "first.json"
    missing = reviews()
    del missing["fact_checks"][5]["checks"]["currency"]
    await query(PortfolioRuntime(path), AsyncMock(return_value={"content": json.dumps(missing)}))
    if legacy_missing_cache:
        saved = json.loads(path.read_text())
        saved["stage_cache"] = {}
        path.write_text(json.dumps(saved))
    second_path = tmp_path / "second.json"
    second = PortfolioRuntime(second_path, path)
    unused = AsyncMock(side_effect=AssertionError("Accepted warnings must not regenerate upstream analysis"))
    await query(second, unused)
    second.save()
    third = PortfolioRuntime(tmp_path / "third.json", second_path)
    result = await query(third, unused)
    unused.assert_not_awaited()
    assert result["warnings"]
    rows = json.loads(result["content"])["fact_checks"]
    assert rows[5]["checks"]["currency"] == "unresolved"
    assert all(set(row["checks"].values()) == {"supported"} for i, row in enumerate(rows) if i != 5)


@pytest.mark.asyncio
async def test_resume_revalidates_saved_allocation_under_current_rules(tmp_path):
    path = tmp_path / "old.json"
    runtime = PortfolioRuntime(path)
    runtime.code = {"old": "manifest"}
    prompt = {"task": "Allocate", "required_schema": {"asset_class_targets": [{}]}}
    bad = {"asset_class_targets": [{"asset_class": "cash", "min_pct": 90, "target_pct": 90, "max_pct": 90}]}
    await runtime.query(AsyncMock(return_value={"content": json.dumps(bad)}), "~deepseek/deepseek-flash-latest",
        [{"role": "user", "content": json.dumps(prompt)}], parser=memo._extract_json_object, validator=lambda *_: [])
    resumed = PortfolioRuntime(tmp_path / "new.json", path)
    good = {"asset_class_targets": [{"asset_class": "cash", "min_pct": 100, "target_pct": 100, "max_pct": 100}]}
    client = AsyncMock(return_value={"content": json.dumps(good)})
    result = await query(resumed, client, prompt)
    assert client.await_count == 1
    assert json.loads(result["content"]) == good
    assert not resumed.receipts[-1]["reused"]


def test_job_health_preserves_warning_without_failed_run(tmp_path):
    from backend.jobs.executor import _analysis_job_output_error
    artifact = {"schema_version": 3, "pipeline_status": "complete", "evidence_brief": {"evidence_status": "complete"},
                "portfolio_snapshot": {"portfolio": {"cash_pct": 100}, "asset_classes": [{"asset_class": "cash", "portfolio_pct": 100}]},
                "macro_positioning": {"asset_class_targets": [{"asset_class": "cash", "min_pct": 100, "target_pct": 100, "max_pct": 100}]},
                "stage_receipts": [{"stage": "review", "input_hash": "review", "status": "failed", "error": "Missing currency"},
                    {"stage": "review", "input_hash": "review", "status": "complete", "warnings": [{"detail": "Currency review remains unresolved"}]}]}
    health = analysis_health(artifact)
    assert health["status"] == "complete"
    assert health["label"] == "Analysis complete with limitations"
    assert health["issues"][0]["severity"] == "warning"
    path = tmp_path / "result.json"
    path.write_text(json.dumps(artifact))
    assert _analysis_job_output_error(path, {"job_type": "portfolio_positioning"}) == ""


@pytest.mark.asyncio
async def test_malformed_cached_stage_is_retried_without_aborting_resume(tmp_path):
    path = tmp_path / "old.json"
    runtime = PortfolioRuntime(path)
    await query(runtime, AsyncMock(return_value={"content": json.dumps(reviews())}))
    saved = json.loads(path.read_text())
    next(iter(saved["stage_cache"].values()))["result"] = None
    path.write_text(json.dumps(saved))
    resumed = PortfolioRuntime(tmp_path / "new.json", path)
    client = AsyncMock(return_value={"content": json.dumps(reviews())})
    result = await query(resumed, client)
    assert client.await_count == 1
    assert result["stage_status"] == "complete"
    assert not result["warnings"]
