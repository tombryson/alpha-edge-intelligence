import asyncio
import json
import threading
import time

import pytest

from backend.portfolio_runtime import PortfolioRuntime, load_record
from backend.portfolio_evidence import validate_stage
from backend.portfolio_recovery import parse_json_object


@pytest.mark.asyncio
async def test_concurrent_saves_coalesce_without_dropping_later_changes(tmp_path, monkeypatch):
    runtime = PortfolioRuntime(tmp_path / "run.checkpoint.json", artifact_path=tmp_path / "run.json")
    started, release = threading.Event(), threading.Event()
    write = runtime._write_snapshot
    writes = []

    def slow_first_write(*args):
        writes.append(args[0])
        if len(writes) == 1:
            started.set()
            assert release.wait(3)
        return write(*args)

    monkeypatch.setattr(runtime, "_write_snapshot", slow_first_write)
    runtime.partial["values"] = []
    first = asyncio.create_task(runtime.asave())
    await asyncio.wait_for(asyncio.to_thread(started.wait, 2), 2.5)
    pending = []
    try:
        for index in range(20):
            runtime.partial["values"].append(index)
            pending.append(asyncio.create_task(runtime.asave()))
        await asyncio.sleep(0)
        assert runtime._save_requested == 21
        assert not any(task.done() for task in pending)
    finally:
        release.set()
        await asyncio.gather(first, *pending)
    assert writes == [1, 2]
    assert runtime.checkpoint_metrics["coalesced_requests"] == 19
    assert runtime.checkpoint_metrics["writes"] == 2
    assert json.loads(runtime.checkpoint.read_text())["partial_artifact"]["values"] == list(range(20))
    assert json.loads(runtime.artifact_path.read_text())["values"] == list(range(20))
    runtime.partial["values"].append(20)
    await runtime.asave()
    assert writes == [1, 2, 3]
    for field in ("snapshot_seconds", "writer_wait_seconds", "record_seconds", "checkpoint_write_seconds", "artifact_write_seconds"):
        assert runtime.checkpoint_metrics[field] >= 0


@pytest.mark.asyncio
async def test_failed_write_does_not_mark_waiting_changes_as_committed(tmp_path, monkeypatch):
    runtime = PortfolioRuntime(tmp_path / "run.checkpoint.json")
    write = runtime._write_snapshot
    failed = False

    def fail_once(*args):
        nonlocal failed
        if not failed:
            failed = True
            raise OSError("disk unavailable")
        return write(*args)

    monkeypatch.setattr(runtime, "_write_snapshot", fail_once)
    runtime.partial["retained"] = "paid result"
    with pytest.raises(OSError):
        await runtime.asave()
    assert runtime._save_committed == 0
    await runtime.asave()
    assert json.loads(runtime.checkpoint.read_text())["partial_artifact"]["retained"] == "paid result"
    assert runtime._save_committed == 2


@pytest.mark.asyncio
async def test_stream_identifier_is_durable_without_blocking_on_full_checkpoint(tmp_path, monkeypatch):
    runtime = PortfolioRuntime(tmp_path / "stream.checkpoint.json")
    write = runtime._write_snapshot

    def delayed_write(*args):
        assert next(iter(runtime.progress.tasks.values()))["activity"] != "awaiting_provider"
        time.sleep(.02)
        return write(*args)

    monkeypatch.setattr(runtime, "_write_snapshot", delayed_write)
    async def client(model, messages, on_progress, **kwargs):
        saved = json.loads(runtime.checkpoint.read_text())["partial_artifact"]["model_request_state"]
        state = next(iter(saved.values()))
        assert state["status"] == "submitting" and state["prepared_at"]
        assert not state.get("started_at")
        before = runtime.checkpoint_metrics["requests"]
        await on_progress({"id": "generation-1", "content_delta": "first"})
        assert runtime.checkpoint_metrics["requests"] == before
        assert "generation-1" in next((tmp_path / ".portfolio-streams").glob("*.jsonl")).read_text()
        return {"content": '{"answer":"saved"}', "finish_reason": "stop"}
    client.supports_progress = True
    await runtime.query(client, "model", [{"role": "user", "content": '{"task":"Test","required_schema":{"answer":"string"}}'}],
        parser=parse_json_object, validator=validate_stage)
    assert runtime.receipts[0]["timing"]["request_checkpoint_seconds"] >= .02
    assert runtime.receipts[0]["status"] == "complete"


def test_stable_records_do_not_get_rehashed_but_nested_changes_do(tmp_path):
    runtime = PortfolioRuntime(tmp_path / "records.checkpoint.json", record_store=True)
    receipt = {"stage": "saved", "status": "complete", "raw_response": {"content": "source " * 100000}}
    runtime.receipts = [receipt]
    runtime.save()
    first = json.loads(runtime.checkpoint.read_text())["stage_receipts"][0]
    hashed = runtime.checkpoint_metrics["record_hashes"]
    runtime.save()
    assert runtime.checkpoint_metrics["record_hashes"] == hashed
    assert runtime.checkpoint_metrics["record_reuses"] > 0
    receipt["raw_response"]["content"] = "changed"
    runtime.save()
    changed = json.loads(runtime.checkpoint.read_text())["stage_receipts"][0]
    assert changed["record_ref"] != first["record_ref"]
    assert load_record(tmp_path, changed)["raw_response"]["content"] == "changed"
    assert load_record(tmp_path, first)["raw_response"]["content"] == "source " * 100000
    runtime.receipts.clear()
    runtime.save()
    assert not runtime._record_memo
