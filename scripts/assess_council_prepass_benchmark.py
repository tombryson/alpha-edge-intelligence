"""Offline measurements for the isolated pilot; no provider requests."""
import json
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.jobs.prepass import _build_stage1_prepass_source_rows_from_bundle
from benchmark_council_prepass import OUT, read, save


def measure():
    metrics = {}
    for case in ("at4", "eiq"):
        reference = read(f"{case}/reference.json")
        save(f"{case}/historical.packet.json", reference["bundle"])
        rows, meta = _build_stage1_prepass_source_rows_from_bundle(OUT / case / "historical.packet.json")
        save(f"{case}/historical.handoff.json", {"rows": rows, "metadata": meta})
        cutoff = reference["manifest"]["generated_at_utc"][:10]
        measurements = {}
        for path in sorted((OUT / case).glob("*.packet.json")):
            name = path.name.removesuffix(".packet.json")
            packet = json.loads(path.read_text())
            rows = read(f"{case}/{name}.handoff.json")["rows"]
            docs = packet["docs"]
            measurements[name] = {
                "documents": len(docs), "handoff_documents": len(rows),
                "packet_characters": len(json.dumps(packet)),
                "handoff_excerpt_characters": sum(len(r["excerpt"]) for r in rows),
                "clipped_rows": sum(r["excerpt"].endswith("...") for r in rows),
                "documents_after_cutoff": [d.get("title") for d in docs if str(d.get("published_at", ""))[:10] > cutoff],
                "unanswered_questions": len(packet.get("unanswered_questions", [])),
                "nonlist_fields": [f"{i}:{field}" for i, d in enumerate(docs) for field in
                    ("key_points", "timeline_milestones", "catalysts_next_12m", "capital_structure", "risks_headwinds")
                    if field in d and not isinstance(d[field], list)],
            }
        receipts = {}
        for path in sorted((OUT / case).glob("*.response.json")):
            data = json.loads(path.read_text())
            receipts[path.name] = {"status": data["status"], "seconds": round(data["seconds"], 2),
                                   "usage": data["body"].get("usage", {})}
        status = read(f"{case}/ultra2x.status.json")
        if status["status"] == "completed":
            start = datetime.fromisoformat(status["created_at"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(status["modified_at"].replace("Z", "+00:00"))
            measurements.get("ultra2x", {})["task_seconds"] = (end-start).total_seconds()
        metrics[case] = {"packets": measurements, "receipts": receipts}
    save("metrics.json", metrics)
    print(json.dumps({k: v["packets"] for k,v in metrics.items()}, indent=2))


if __name__ == "__main__":
    measure()
