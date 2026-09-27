#!/usr/bin/env python3
"""Offline replay of saved portfolio research processing; never contacts model APIs."""

import argparse
import asyncio
import hashlib
import json
import tempfile
from pathlib import Path

from backend.portfolio_evidence import apply_fact_checks, validate_stage
from backend.portfolio_runtime import CURRENT_LANE, PortfolioRuntime
from portfolio_positioning_memo import _extract_json_object


async def audit(run_path, checkpoint_path):
    original = run_path.read_bytes()
    artifact = json.loads(original)
    receipts = artifact["stage_receipts"]
    stages = {}
    for receipt in receipts:
        if receipt.get("prompt") and ("Review source support / batch" in receipt["stage"] or
                "Extract source-linked facts" in receipt["stage"] or "Build source-grounded portfolio evidence" in receipt["stage"]):
            stages.setdefault(receipt["input_hash"], receipt)
    requests, results = [], []

    async def offline_repair(model, messages, **kwargs):
        prompt = json.loads(messages[0]["content"])
        if not prompt.get("repair_fields"):
            raise AssertionError("Completed work was not reused; refusing an unplanned model request")
        requests.append({"model": model, "repair_fields": prompt["repair_fields"],
                         "fact_count": len(prompt["evidence"]["facts"])})
        # Exercise the worst case: the targeted repair still supplies no verdict.
        return {"content": '{"fact_checks":[]}', "finish_reason": "stop", "id": "offline-repair-only"}

    with tempfile.TemporaryDirectory(prefix="portfolio-review-replay-") as directory:
        runtime = PortfolioRuntime(Path(directory) / "replay.checkpoint.json", checkpoint_path)
        for receipt in stages.values():
            token = CURRENT_LANE.set(receipt["stage"].split(":", 1)[0])
            settings = {key: value for key, value in receipt["request_settings"].items() if key != "response_format"}
            try:
                result = await runtime.query(offline_repair, receipt["model"],
                    [{"role": "user", "content": json.dumps(receipt["prompt"])}],
                    parser=_extract_json_object, validator=validate_stage, **settings)
            finally:
                CURRENT_LANE.reset(token)
            assert result["stage_status"] == "complete", receipt["stage"]
            results.append(result)
        checks = [check for result in results for check in json.loads(result["content"]).get("fact_checks", [])]
        evidence = artifact["evidence_brief"]
        facts = apply_fact_checks(evidence["facts"], checks, evidence["source_packet"])
        assert len(facts) == len(evidence["facts"])
        assert len(checks) == len(facts)
        report = {"offline": True, "provider_requests": 0, "run": artifact["id"],
                  "reused_stages": sum(bool(row.get("reused")) for row in runtime.receipts),
                  "completed_stages": len(results), "retained_facts": len(facts),
                  "retained_sources": len(evidence["source_packet"]["sources"]),
                  "simulated_repairs": requests,
                  "warnings": [warning for result in results for warning in result.get("warnings", [])],
                  "original_sha256": hashlib.sha256(original).hexdigest()}
    assert run_path.read_bytes() == original
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve() in {args.run.resolve(), args.checkpoint.resolve()}:
        parser.error("Report must not overwrite either source artifact")
    report = asyncio.run(audit(args.run, args.checkpoint))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
