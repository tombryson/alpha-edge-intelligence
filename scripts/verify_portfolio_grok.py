#!/usr/bin/env python3
"""Paid, explicit diagnostic: replay only saved Grok prompts, never the portfolio pipeline."""

import argparse
import asyncio
import importlib.util
import json
import os
from pathlib import Path


async def main(args):
    spec = importlib.util.spec_from_file_location("xai_diagnostic", args.client)
    client = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(client)
    artifact = json.loads(Path(args.artifact).read_text())
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    async def verify(lane):
        label = lane["label"]
        saved = lane.get("macro_news") or {}
        prompt = saved.get("prompt")
        if not prompt:
            raise ValueError(f"No original Grok prompt retained for {label}")
        result = await client.fetch_xai_research(
            api_key=os.getenv("XAI_API_KEY", ""),
            api_url=os.getenv("XAI_API_URL", "https://api.x.ai/v1/responses"),
            model=saved.get("model") or "grok-4.6", prompt=prompt,
            on_progress=lambda event: print(json.dumps({"lane": label, **event}), flush=True),
        )
        (output / f"{label}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
        report = {key: result.get(key) for key in ("success", "error", "error_type", "model", "request_count", "request_id", "tool_calls_count", "finish_reason", "usage")}
        report.update(lane=label, summary_chars=len(result.get("summary") or ""), citations=len(result.get("results") or []),
                      elapsed_seconds=sum(row["elapsed_seconds"] for row in result.get("attempts") or []))
        print(json.dumps(report), flush=True)
        return report

    reports = await asyncio.gather(*(verify(lane) for lane in artifact["evidence_runs"]))
    (output / "summary.json").write_text(json.dumps(reports, indent=2))
    return 0 if all(row["success"] for row in reports) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact")
    parser.add_argument("--client", default=str(Path(__file__).resolve().parents[1] / "backend/research/providers/xai.py"))
    parser.add_argument("--output-dir", required=True)
    raise SystemExit(asyncio.run(main(parser.parse_args())))
