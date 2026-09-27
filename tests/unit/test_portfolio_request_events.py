import asyncio
import json
import threading

import pytest

from backend.portfolio_runtime import PortfolioRuntime, load_checkpoint, load_cache_entry


@pytest.mark.asyncio
async def test_request_events_recover_after_crash_without_rewriting_large_artifact(tmp_path):
    path = tmp_path / "run.checkpoint.json"
    runtime = PortfolioRuntime(path, artifact_path=tmp_path / "run.json", record_store=True)
    runtime.partial["research"] = {"passage": "retained evidence " * 100000}
    await runtime.asave()
    original = path.read_bytes(), runtime.artifact_path.read_bytes()
    runtime.partial["model_request_state"] = {"pending": {"status": "submitting"}}
    await runtime.asave_request("pending")
    receipt = {"input_hash": "done", "stage": "review", "status": "complete", "request_id": "provider-1"}
    runtime.receipts.append(receipt)
    runtime.cache["done"] = {"receipt": receipt, "result": {"content": "paid answer", "stage_status": "complete"}}
    await runtime.asave_request("done")
    assert (path.read_bytes(), runtime.artifact_path.read_bytes()) == original
    recovered = load_checkpoint(path)
    assert recovered["partial_artifact"]["model_request_state"]["pending"]["status"] == "submitting"
    assert load_cache_entry(path.parent, recovered["stage_cache"]["done"])["result"]["content"] == "paid answer"
    resumed = PortfolioRuntime(tmp_path / "resume.checkpoint.json", resume=path, record_store=True)
    assert resumed.cache["done"]["result"]["content"] == "paid answer"
    assert resumed.partial["model_request_state"]["pending"]["status"] == "submitting"
    assert runtime.checkpoint_metrics["writes"] == 1
    assert runtime.checkpoint_metrics["request_event_bytes"] < 10000


@pytest.mark.asyncio
async def test_materialization_does_not_replay_stale_events_or_duplicate_receipts(tmp_path):
    runtime = PortfolioRuntime(tmp_path / "run.checkpoint.json", record_store=True)
    await runtime.asave()
    runtime.partial["model_request_state"] = {"a": {"status": "submitting"}}
    await runtime.asave_request("a")
    runtime.partial["model_request_state"]["a"] = {"status": "complete", "provider_request_id": "accepted"}
    runtime.receipts.append({"input_hash": "a", "stage": "test", "status": "complete"})
    await runtime.asave_request("a")
    await runtime.asave()
    assert load_checkpoint(runtime.checkpoint)["partial_artifact"]["model_request_state"]["a"]["status"] == "complete"
    assert len(load_checkpoint(runtime.checkpoint)["stage_receipts"]) == 1
    assert json.loads(runtime.checkpoint.read_text())["request_event_sequence"] == 2


@pytest.mark.asyncio
async def test_concurrent_events_keep_every_accepted_result_and_disk_errors_propagate(tmp_path, monkeypatch):
    runtime = PortfolioRuntime(tmp_path / "run.checkpoint.json", record_store=True)
    await runtime.asave()
    for i in range(10):
        key = str(i)
        row = {"input_hash": key, "stage": "test", "status": "complete"}
        runtime.receipts.append(row)
        runtime.cache[key] = {"receipt": row, "result": {"content": key}}
    await asyncio.gather(*(runtime.asave_request(str(i)) for i in range(10)))
    saved = load_checkpoint(runtime.checkpoint)
    assert len(saved["stage_cache"]) == len(saved["stage_receipts"]) == 10
    def fail(event):
        raise OSError("disk full")
    monkeypatch.setattr(runtime, "_write_request_event", fail)
    with pytest.raises(OSError, match="disk full"):
        await runtime.asave_request("new")
    assert runtime._request_event_sequence == 10
    assert runtime.progress.checkpoint["status"] == "failed"


@pytest.mark.asyncio
async def test_cancelled_writer_does_not_allow_the_next_result_to_overwrite_its_event(tmp_path, monkeypatch):
    runtime = PortfolioRuntime(tmp_path / "run.checkpoint.json", record_store=True)
    await runtime.asave()
    entered, release = threading.Event(), threading.Event()
    write = runtime._write_request_event
    def delayed(event):
        if event["sequence"] == 1:
            entered.set()
            assert release.wait(3)
        return write(event)
    monkeypatch.setattr(runtime, "_write_request_event", delayed)
    for key in ("first", "second"):
        receipt = {"input_hash": key, "stage": "test", "status": "complete"}
        runtime.cache[key] = {"receipt": receipt, "result": {"content": key}}
    first = asyncio.create_task(runtime.asave_request("first"))
    await asyncio.to_thread(entered.wait, 2)
    first.cancel()
    second = asyncio.create_task(runtime.asave_request("second"))
    await asyncio.sleep(0)
    first.cancel()
    await asyncio.sleep(0)
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await first
    await second
    assert runtime._request_event_sequence == 2
    assert set(load_checkpoint(runtime.checkpoint)["stage_cache"]) == {"first", "second"}
