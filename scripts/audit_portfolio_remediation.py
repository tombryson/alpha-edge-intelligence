"""Offline workload and persistence acceptance against an immutable saved portfolio."""

import argparse
import asyncio
from hashlib import sha256
import json
from pathlib import Path
import resource
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.portfolio_evidence import reusable_fact_checks
from backend.portfolio_independent import review_prompt_batches
from backend.portfolio_judgment import financial_case_issues, play_expression_issues
from backend.portfolio_runtime import PortfolioRuntime, business_data, load_checkpoint, load_cache_entry
from backend.portfolio_tasks import decision_source_check_plan, fact_review_batches


def encoded_size(value):
    return len(json.dumps(value, ensure_ascii=False).encode())


async def benchmark(path):
    raw = path.read_bytes()
    run = json.loads(raw)
    evidence = run["evidence_brief"]
    started = time.monotonic()
    parts = review_prompt_batches("defensive_regime_reviewer", evidence, run["independent_research_context"],
        run["independent_ideal"], run["current_portfolio_assessment"], run["portfolio_snapshot"], run["investment_plays"])
    review_seconds = time.monotonic() - started
    plan = decision_source_check_plan(evidence, run["provisional_recommendation"], run["analytical_reviews"])
    _, pending = reusable_fact_checks(evidence["facts"], evidence["source_packet"])
    pending = [fact for fact in pending if fact["id"] in plan["fact_ids"]]
    batches = fact_review_batches(pending, evidence["source_packet"])
    persistence = {}
    with tempfile.TemporaryDirectory(prefix="portfolio-offline-acceptance-") as folder:
        checkpoint = Path(folder) / "run.checkpoint.json"
        runtime = PortfolioRuntime(checkpoint, artifact_path=Path(folder) / "run.json", record_store=True)
        runtime._report_progress = lambda: None
        runtime.partial = business_data(run)
        lags = []
        done = asyncio.Event()
        async def clock():
            while not done.is_set():
                before = time.monotonic()
                await asyncio.sleep(.01)
                lags.append(max(0, time.monotonic() - before - .01))
        heartbeat = asyncio.create_task(clock())
        try:
            await asyncio.sleep(0)
            start = time.monotonic()
            await runtime.asave()
            persistence["full_checkpoint_seconds"] = time.monotonic() - start
            initial = sha256(checkpoint.read_bytes()).hexdigest(), sha256(runtime.artifact_path.read_bytes()).hexdigest()
            persistence["materialized_bytes"] = checkpoint.stat().st_size + runtime.artifact_path.stat().st_size
            await asyncio.sleep(.02)
            lags.clear()
            async def complete(index):
                key = f"offline-{index}"
                receipt = {"input_hash": key, "stage": "offline fake result", "status": "complete", "request_id": key}
                runtime.receipts.append(receipt)
                runtime.cache[key] = {"receipt": receipt, "result": {"content": f"saved observation {index} " * 1000}}
                runtime.partial.setdefault("model_request_state", {})[key] = {"status": "complete", "provider_request_id": key}
                await runtime.asave_request(key)
            start = time.monotonic()
            await asyncio.gather(*(complete(i) for i in range(20)))
            persistence["twenty_concurrent_result_seconds"] = time.monotonic() - start
            await asyncio.sleep(.02)
            persistence["max_result_event_loop_lag_seconds"] = max(lags, default=0)
            persistence["request_events"] = runtime.checkpoint_metrics["request_events"]
            persistence["event_manifest_bytes"] = runtime.checkpoint_metrics["request_event_bytes"]
            persistence["total_incremental_bytes"] = sum(p.stat().st_size for p in Path(folder).rglob("*") if p.is_file()) - persistence["materialized_bytes"]
            assert initial == (sha256(checkpoint.read_bytes()).hexdigest(), sha256(runtime.artifact_path.read_bytes()).hexdigest())
            restored = load_checkpoint(checkpoint)
            assert len(restored["stage_cache"]) == 20
            for i in range(20):
                assert load_cache_entry(checkpoint.parent, restored["stage_cache"][f"offline-{i}"])["result"]["content"] == f"saved observation {i} " * 1000
            persistence["recovered_results"] = 20
            persistence["full_rewrites_for_result_events"] = runtime.checkpoint_metrics["writes"] - 1
        finally:
            done.set()
            await heartbeat
    assert sha256(path.read_bytes()).hexdigest() == sha256(raw).hexdigest()
    return {"artifact": str(path), "sha256": sha256(raw).hexdigest(), "input_unchanged": True,
        "provider_requests": 0, "review": {"sections_per_reviewer": len(parts), "total_bytes_per_reviewer": sum(map(encoded_size, parts)),
            "largest_bytes": max(map(encoded_size, parts)), "construction_seconds": review_seconds,
            "economic_cases": len({case["id"] for part in parts for case in part["review_scope"]["economic_cases"]})},
        "source_checks": {"selected_observations": len(pending), "batches": len(batches),
            "total_batch_bytes": sum(map(encoded_size, batches)), "missing_ids": plan["missing_fact_ids"]},
        "persistence": persistence, "peak_process_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024),
        "financial_case_issues": financial_case_issues(run["provisional_recommendation"], evidence),
        "play_expression_issues": play_expression_issues(run["provisional_recommendation"]),
        "limits": ["Fake result replay, not provider latency or live cost.", "Does not establish final financial quality or completed memo readability.",
                   "Full phase checkpoints still copy and materialize the assembled analysis."]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = asyncio.run(benchmark(args.artifact))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key not in {"financial_case_issues", "play_expression_issues"}}, indent=2))
