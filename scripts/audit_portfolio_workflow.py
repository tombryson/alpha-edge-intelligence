"""Offline saved-research-to-reader acceptance; no network or financial re-analysis."""

import argparse
import asyncio
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import resource
import sys
import tempfile
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.portfolio_evidence import review_fields
from backend.portfolio_runtime import CURRENT_LANE, CURRENT_RUNTIME, PortfolioRuntime, load_checkpoint, write_json_atomic
from scripts import portfolio_positioning_memo as memo


def empty_shape(schema):
    if isinstance(schema, dict):
        return {key: empty_shape(value) for key, value in schema.items()}
    return [] if isinstance(schema, list) else None


async def replay(path):
    raw = path.read_bytes()
    original_hash = hashlib.sha256(raw).hexdigest()
    original = json.loads(raw)
    calls, trace, research_calls = [], [], []
    fault_sent = False
    active = peak_active = 0
    started = time.monotonic()
    evidence = deepcopy(original["evidence_brief"])

    async def retained_sources(**kwargs):
        return deepcopy(evidence), deepcopy(original.get("evidence_runs", [])), deepcopy(original.get("source_citations", []))

    async def no_network(*args, **kwargs):
        raise AssertionError("Offline acceptance must never access the network")

    async def unavailable_supplement(provider, runtime, **kwargs):
        research_calls.append(kwargs.get("question"))
        async def unavailable():
            return {"error": "Simulated supplementary research unavailable", "error_type": "provider_error",
                    "http_status": 503, "results": [], "resumable": False}
        return await runtime.research("parallel", {"provider": "parallel", "question": kwargs.get("question")}, unavailable, required=False)

    async def client(model, messages, on_progress=None, **kwargs):
        nonlocal fault_sent, active, peak_active
        prompt = json.loads(messages[0]["content"])
        task = prompt["task"]
        calls.append({"task": task, "bytes": len(messages[0]["content"].encode()), "model": model})
        trace.append({"event": "start", "task": task, "at": time.monotonic() - started})
        active += 1
        peak_active = max(peak_active, active)
        try:
            if on_progress:
                await on_progress({"id": "offline-" + str(len(calls)), "activity": "awaiting_provider"})
            await asyncio.sleep(.002)
            result = empty_shape(prompt["required_schema"])
            if "asset_class_targets" in result:
                if "independent ideal" in task:
                    assert "current_portfolio" not in prompt and "investment_plays" not in prompt
                    result.update(deepcopy(original["independent_ideal"]))
                elif "current portfolio independently" in task:
                    assert "independent_ideal" not in prompt and "investment_plays" not in prompt
                    result.update(deepcopy(original["current_portfolio_assessment"]))
                else:
                    result.update(deepcopy(original["provisional_recommendation"]))
            elif "fact_checks" in result:
                if not fault_sent:
                    fault_sent = True
                    return {"content": "", "error": "Simulated terminal source-check failure", "error_type": "provider_error",
                            "error_retryable": False, "outcome_uncertain": False}
                result["fact_checks"] = [{"fact_id": row["id"],
                    "checks": {field: "unresolved" for field in review_fields(row)},
                    "reason": "Offline simulator does not independently verify market evidence"}
                    for row in prompt["evidence"]["facts"]]
            elif "allocation_details" in result:
                result["allocation_details"] = [{"asset_class": row["asset_class"], "implementation": {},
                    "market_pricing": {}, "investment_case": {"downside": "Unresolved in offline simulation"},
                    "alternatives": []} for row in prompt["assigned_allocations"]]
            elif "target_updates" in result:
                result.update(reason="Offline unchanged allocation", target_updates=[], removed_target_ids=[], updates={})
            elif "comparison_summary" in result:
                result.update(comparison_summary="Offline workflow acceptance, not new investment analysis.",
                    portfolio_level_comments=["The saved investment hypotheses remain conditional on their recorded evidence."], asset_class_comments=[])
            elif "findings" in result:
                role = "defensive_regime_reviewer" if "Defensive" in task or "defensive" in task else "exposure_equivalence_reviewer"
                source = next((review for review in original["analytical_reviews"] if review.get("council_lane") == role), {})
                shown = {row["id"] for row in (prompt.get("evidence_brief") or {}).get("facts", [])}
                result.update(summary="Offline retained review arguments", findings=[deepcopy(row) for row in source.get("findings", [])
                    if set(row.get("fact_ids") or []) & shown])
                # Exercise one bounded archived-source lookup in each role.
                if not any(row["task"] == "Resolve material review questions using requested archived source excerpts" for row in calls):
                    unseen = next((row["id"] for row in evidence["facts"] if row["id"] not in shown), None)
                    if unseen:
                        result["evidence_requests"] = [{"fact_ids": [unseen], "reason": "Offline exercise of retained source lookup"}]
            elif "summary" in result:
                result["summary"] = "Offline consistency assessment; no new investment judgment"
            # Keep submitted components so the normal component-completeness path runs.
            if "play_components" in result:
                result["play_components"] = [{"play_id": play["id"], "components": deepcopy(play.get("components", [])),
                    "coverage_status": "complete", "coverage_reason": "Retained original test inventory", "unresolved_source_text": []}
                    for play in original.get("investment_plays", [])]
            response = {"content": json.dumps(result), "finish_reason": "stop", "id": "offline-" + str(len(calls))}
            if on_progress:
                await on_progress({"content_delta": response["content"]})
            return response
        finally:
            active -= 1
            trace.append({"event": "finish", "task": task, "at": time.monotonic() - started})
    client.supports_progress = True

    with tempfile.TemporaryDirectory(prefix="portfolio-workflow-acceptance-") as folder:
        folder = Path(folder)
        context_path, destination = folder / "context.json", folder / "memo.json"
        write_json_atomic(context_path, original["portfolio_context"])
        runtime = PortfolioRuntime(folder / "memo.checkpoint.json", artifact_path=destination, record_store=True)
        runtime.started_at = original.get("provenance", {}).get("research_cutoff") or original["independent_research_context"]["research_cutoff"]
        runtime._report_progress = lambda: None
        queries = []
        original_query = runtime.query
        async def tracked_query(client, model, messages, **kwargs):
            lane = CURRENT_LANE.get()
            result = await original_query(client, model, messages, **kwargs)
            if result.get("stage_status") == "complete":
                queries.append((lane, model, deepcopy(messages), dict(kwargs), result["content"]))
            return result
        runtime.query = tracked_query
        args = argparse.Namespace(portfolio_context_file=str(context_path), dump_json=str(destination),
            query="", mode="deep", run_label="Offline fixture acceptance", resume_checkpoint=None)
        token = CURRENT_RUNTIME.set(runtime)
        try:
            with patch.object(memo, "_run_evidence_ensemble", retained_sources), patch.object(memo, "query_model", client), \
                 patch("backend.portfolio_retrieval.ParallelSourceProvider.gather", unavailable_supplement), \
                 patch("backend.portfolio_documents.fetch_document_context", no_network), \
                 patch("httpx.AsyncClient.send", no_network):
                artifact = await memo._run_pipeline(args)
            runtime.persist_artifact(artifact)
            restored = load_checkpoint(runtime.checkpoint)
            assert artifact.get("analyst_memo_markdown")
            assert artifact.get("macro_positioning", {}).get("asset_class_targets")
            assert restored["stage_cache"]
            assert len(artifact["evidence_brief"]["facts"]) >= len(evidence["facts"])
            assert artifact["portfolio_context"] == original["portfolio_context"]
            totals = sum(row["target_pct"] for row in artifact["macro_positioning"]["asset_class_targets"])
            assert abs(totals - 100) < .01
            pipeline_peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024)
            # Re-open the content-addressed checkpoint as a new worker and exercise
            # the real cache admission/validation path for every completed request.
            resumed = PortfolioRuntime(folder / "resumed.checkpoint.json", resume=runtime.checkpoint, record_store=True)
            resumed._report_progress = lambda: None
            for lane, model, messages, options, content in queries:
                lane_token = CURRENT_LANE.set(lane)
                try:
                    answer = await resumed.query(no_network, model, messages, **options)
                    assert answer["content"] == content
                    assert resumed.receipts[-1].get("reused")
                finally:
                    CURRENT_LANE.reset(lane_token)
            details_starts = [row["at"] for row in trace if row["event"] == "start" and "investment details" in row["task"]]
            source_finishes = [row["at"] for row in trace if row["event"] == "finish" and "Review source support" in row["task"]]
            report = {"artifact_sha256": original_hash, "network_requests": 0, "input_bytes": len(raw),
                "elapsed_seconds": time.monotonic() - started, "simulated_model_requests": len(calls),
                "simulated_research_failures": len(research_calls), "terminal_source_failure_injected": fault_sent,
                "peak_active_models": peak_active, "case_source_overlap": bool(details_starts and source_finishes and min(details_starts) < max(source_finishes)),
                "pipeline_status": artifact.get("pipeline_status"), "final_weight_total": totals,
                "memo_characters": len(artifact["analyst_memo_markdown"]), "recoverable_cache_entries": len(restored["stage_cache"]),
                "completed_requests_revalidated_on_resume": len(queries),
                "checkpoint_metrics": runtime.checkpoint_metrics, "work_plan": artifact.get("work_plan"),
                "tasks": dict(Counter(row["task"] for row in calls)), "trace": trace,
                "request_bytes": sum(row["bytes"] for row in calls),
                "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024),
                "pipeline_peak_rss_before_resume_bytes": pipeline_peak_rss,
                "limits": ["Starts from preserved research; tests downstream orchestration, not source-provider quality.",
                           "Model outputs are synthetic or retained fixture values, not new financial analysis or live latency.",
                           "Peak harness RSS includes both original and resumed runtimes in one process."]}
        finally:
            CURRENT_RUNTIME.reset(token)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == original_hash
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = asyncio.run(replay(args.artifact))
    write_json_atomic(args.output, result, indent=2)
    print(json.dumps({key: value for key, value in result.items() if key not in {"trace", "tasks", "work_plan"}}, indent=2))
