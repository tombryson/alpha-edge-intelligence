"""September 23 audit regressions; never call paid providers."""

import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import sys

import pytest

from backend.portfolio_evidence import normalize_facts, review_fields
from backend.portfolio_runtime import CURRENT_RUNTIME, PortfolioRuntime, load_checkpoint
from scripts import portfolio_positioning_memo as memo


@pytest.mark.asyncio
async def test_model_change_retains_checks_but_changed_evidence_is_reviewed(tmp_path, monkeypatch):
    source = {"id": "s", "url": "https://example.test/gdp", "excerpt": "GDP growth 3.1 percent", "published_at": "2026-09-15"}
    packet = {"as_of": "2026-09-22", "sources": [source]}
    fact = {"id": "a", "kind": "observed_macro", "metric": "GDP growth", "value": 3.1,
            "unit": "percent", "currency": "not_applicable", "benchmark": "GDP",
            "observed_at": "2026-09-15", "published_at": "2026-09-15",
            "source_ids": ["s"], "source_excerpt": source["excerpt"]}
    brief = {"facts": normalize_facts([fact], packet), "source_packet": packet, "evidence_status": "complete"}
    calls = []

    async def fake_query(model, messages, **kwargs):
        rows = json.loads(messages[0]["content"])["evidence"]["facts"]
        calls.append(model)
        return {"stage_status": "complete", "content": json.dumps({"fact_checks": [
            {"fact_id": row["id"], "checks": {field: "unresolved" for field in review_fields(row)},
             "reason": "Publication metadata is incomplete"} for row in rows]})}

    monkeypatch.setattr(memo, "_query_stage", fake_query)
    monkeypatch.setattr(memo, "_summary_model_for_mode", lambda mode: "model-a")
    runtime = PortfolioRuntime(tmp_path / "run.checkpoint.json", record_store=True)
    token = CURRENT_RUNTIME.set(runtime)
    try:
        checked = await memo._run_evidence_reconciliation(query="portfolio", mode="deep",
            evidence_briefs=[deepcopy(brief)], asset_class_vocabulary=[], review_fact_ids={"a"})
        assert calls == ["model-a"]
        monkeypatch.setattr(memo, "_summary_model_for_mode", lambda mode: "model-b")
        reused = await memo._run_evidence_reconciliation(query="portfolio", mode="deep",
            evidence_briefs=[checked], asset_class_vocabulary=[], review_fact_ids={"a"})
        assert calls == ["model-a"]
        assert reused["facts"][0]["claim_review"]["check_model"] == "model-a"
        changed = deepcopy(reused)
        changed["facts"][0]["value"] = 2.9
        await memo._run_evidence_reconciliation(query="portfolio", mode="deep",
            evidence_briefs=[changed], asset_class_vocabulary=[], review_fact_ids={"a"})
        assert calls == ["model-a", "model-b"]
    finally:
        CURRENT_RUNTIME.reset(token)


@pytest.mark.asyncio
@pytest.mark.skipif(os.name != "posix", reason="Production worker cancellation uses POSIX SIGTERM")
async def test_real_worker_termination_drains_received_result(tmp_path, monkeypatch):
    from backend.jobs import executor, state

    monkeypatch.setattr(executor, "ANALYSIS_JOBS", {})
    monkeypatch.setattr(executor, "JOBS_META_DIR", tmp_path / "jobs")
    monkeypatch.setattr(executor, "_ensure_analysis_job_dirs", lambda: (tmp_path / "jobs").mkdir(exist_ok=True))
    monkeypatch.setattr(state, "ANALYSIS_JOB_PROCESSES", {})
    monkeypatch.setattr(state, "ANALYSIS_JOB_PREPARATIONS", {})
    checkpoint = tmp_path / "run.checkpoint.json"
    # Exercise the same handled SIGTERM used by the production entry point,
    # while a received result is waiting for its durable event write.
    worker = '''
import argparse, asyncio, sys, time
from pathlib import Path
from backend.portfolio_runtime import CURRENT_RUNTIME
from scripts import portfolio_positioning_memo as memo
async def fake_pipeline(args):
    runtime = CURRENT_RUNTIME.get()
    runtime._report_progress = lambda: None
    await runtime.asave()
    runtime.receipts.append({"input_hash": "received", "status": "complete"})
    runtime.cache["received"] = {"receipt": runtime.receipts[-1], "result": {"content": "retained result"}}
    write = runtime._write_request_event
    def delayed(event):
        print("WRITE_STARTED", flush=True)
        time.sleep(0.3)
        return write(event)
    runtime._write_request_event = delayed
    await runtime.asave_request("received")
    await asyncio.sleep(60)
memo._run_pipeline = fake_pipeline
memo.FundingGuard = lambda: None
args = argparse.Namespace(dump_json=str(Path(sys.argv[1]).with_name("run.json")), resume_checkpoint=None)
raise SystemExit(asyncio.run(memo._async_main(args)))
'''
    process = await asyncio.create_subprocess_exec(sys.executable, "-c", worker, str(checkpoint),
        cwd=str(Path(__file__).resolve().parents[2]), stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    executor.ANALYSIS_JOBS["audit"] = {"job_id": "audit", "status": "running"}
    state.ANALYSIS_JOB_PROCESSES["audit"] = process
    try:
        line = await asyncio.wait_for(process.stdout.readline(), timeout=15)
        assert line.strip() == b"WRITE_STARTED"
        await executor.cancel_analysis_job("audit")
        await asyncio.wait_for(process.wait(), timeout=15)
        await process._council_cancel_waiter
        assert "received" in load_checkpoint(checkpoint)["stage_cache"]
        assert process.returncode == 130
        assert json.loads(checkpoint.with_name("run.json").read_text())["pipeline_status"] == "cancelled"
    finally:
        if process.returncode is None:
            process.kill()
        await process.wait()


def test_observed_causal_link_requires_source_support_not_only_existing_id():
    from backend.portfolio_judgment import financial_case_issues

    proposal = {"asset_class_targets": [{"asset_class": "producers", "target_pct": 10,
        "investment_case": {"sizing_tradeoff": "Ten percent instead of fifteen limits common-factor exposure.",
            "causal_chain": [{"link": "Higher commodity prices improve free cash flow",
                             "basis": "observed", "fact_ids": ["unverified"]}]}}]}
    evidence = {"facts": [{"id": "unverified", "claim_status": "unresolved"}]}
    issues = financial_case_issues(proposal, evidence)
    assert issues and issues[0]["unsubstantiated_observed_links"]


def test_equivalent_display_wording_does_not_create_identity_issue():
    from backend.portfolio_judgment import play_expression_issues

    proposal = {"asset_class_targets": [{"asset_class": "GOLD_MINERS", "display_name": "Gold Miners"}],
        "play_assessments": [{"play_id": "scarcity", "expressions": [
            {"asset_class": "GOLD_MINERS", "display_name": "Gold miner equities"}]}]}
    assert play_expression_issues(proposal) == []
