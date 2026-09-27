#!/usr/bin/env python3
"""Verify reuse of completed checkpoint stages offline, including retained warnings."""

import argparse
import asyncio
import itertools
import json
from pathlib import Path

from backend.portfolio_evidence import validate_stage
from backend.portfolio_runtime import CURRENT_LANE, PortfolioRuntime, business_data, digest
from portfolio_positioning_memo import _extract_json_object


def original_settings(receipt, code):
    settings = {k: v for k, v in receipt["request_settings"].items() if k != "response_format"}
    contract = {"stage": receipt["stage"], "model": receipt["model"],
                "prompt": business_data(receipt["prompt"]), "contract": 3, "code": code}
    candidates = [settings]
    # Older receipts recorded final-attempt settings, not the original cache contract.
    for budget, effort in itertools.product((12000, 16000, 24000, 32000, 48000, 64000, 5000), ("low", "medium", "high", "")):
        candidates.append({**settings, "max_tokens": budget, "reasoning_effort": effort})
    for candidate in candidates:
        if digest({**contract, "settings": candidate}) == receipt["input_hash"]:
            return candidate
    raise ValueError(f"Cannot reconstruct request settings: {receipt['stage']}")


async def audit(path):
    runtime = PortfolioRuntime(resume=path)
    latest = {r["input_hash"]: r for r in runtime.previous_receipts if r.get("prompt")}
    requests = []

    async def unavailable_client(model, messages, **kwargs):
        requests.append(json.loads(messages[0]["content"])["task"])
        raise RuntimeError("Offline audit forbids model requests")

    checked, warnings = 0, 0
    for receipt in latest.values():
        if receipt["status"] != "complete":
            continue
        settings = original_settings(receipt, runtime.previous_code)
        token = CURRENT_LANE.set(receipt["stage"].split(":", 1)[0])
        try:
            result = await runtime.query(unavailable_client, receipt["model"],
                [{"role": "user", "content": json.dumps(receipt["prompt"])}],
                parser=_extract_json_object, validator=validate_stage, **settings)
        finally:
            CURRENT_LANE.reset(token)
        assert result["stage_status"] == "complete", receipt["stage"]
        assert result.get("warnings", []) == receipt.get("warnings", []), receipt["stage"]
        if receipt.get("retained_output") is not None:
            assert json.loads(result["content"]) == receipt["retained_output"], receipt["stage"]
        checked += 1
        warnings += bool(result.get("warnings"))
    assert not requests, f"Completed stages would be regenerated: {requests}"
    assert all(r.get("reused") for r in runtime.receipts)
    return {"offline": True, "model_requests": 0, "structured_stages_reused": checked,
            "completed_with_limitations_preserved": warnings, "checkpoint": path.name}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(audit(args.checkpoint)), indent=2))
