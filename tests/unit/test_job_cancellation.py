import asyncio
import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from backend.jobs import executor, state


@pytest.fixture
def job_store(tmp_path, monkeypatch):
    monkeypatch.setattr(executor, "JOBS_META_DIR", tmp_path)
    monkeypatch.setattr(executor, "_ensure_analysis_job_dirs", lambda: None)
    monkeypatch.setattr(executor, "ANALYSIS_JOBS", {})
    monkeypatch.setattr(state, "ANALYSIS_JOB_PROCESSES", {})
    monkeypatch.setattr(state, "ANALYSIS_JOB_PREPARATIONS", {})
    return executor.ANALYSIS_JOBS


@pytest.mark.asyncio
async def test_queued_cancel_never_starts_worker(job_store, monkeypatch, tmp_path):
    job_store["queued"] = {"job_id": "queued", "status": "queued"}
    job = await executor.cancel_analysis_job("queued")
    assert job["status"] == "cancelled"
    def forbidden(*args, **kwargs):
        pytest.fail("Cancelled queued work must not spawn")
    monkeypatch.setattr(asyncio, "create_subprocess_exec", forbidden)
    await executor._run_analysis_job(job_id="queued", command=["unused"], output_path=tmp_path / "run.json", request_payload={})
    await executor._set_job_fields("queued", status="running", stage_message="late progress")
    assert job["status"] == "cancelled"
    assert "Stopping" in job["stage_message"]


@pytest.mark.asyncio
async def test_cancel_only_signals_owned_process_and_preserves_results(job_store, tmp_path):
    output = tmp_path / "run.json"
    output.write_text('{"saved":"research"}')
    process = await asyncio.create_subprocess_exec("sleep", "60")
    state.ANALYSIS_JOB_PROCESSES["active"] = process
    job_store["active"] = {"job_id": "active", "status": "running", "pid": 999999,
                           "output_path": str(output), "execution_progress": {"status": "running"}}
    job_store["other"] = {"job_id": "other", "status": "running"}
    try:
        job = await executor.cancel_analysis_job("active")
        await asyncio.wait_for(process.wait(), 3)
        await process._council_cancel_waiter
        assert job["status"] == "cancelling"
        assert job_store["other"]["status"] == "running"
        assert output.read_text() == '{"saved":"research"}'
        assert executor._public_job_view(job)["execution_progress"]["status"] == "cancelling"
        await executor._set_job_fields("active", status="cancelled", finished_at="stopped")
        await executor._append_job_stream_line("active", "stdout_tail", 'portfolio progress: {"execution_progress":{"status":"running","message":"late","current_phase":"research"}}')
        assert job["status"] == "cancelled" and job["stage_message"] != "late"
        loaded = executor._load_analysis_jobs_from_disk()
        assert loaded["active"]["status"] == "cancelled"
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()


@pytest.mark.asyncio
async def test_other_instance_cannot_be_cancelled(job_store):
    job_store["remote"] = {"job_id": "remote", "status": "running", "instance_id": "other"}
    with pytest.raises(HTTPException) as exc:
        await executor.cancel_analysis_job("remote")
    assert exc.value.status_code == 409
    assert not job_store["remote"].get("cancel_requested_at")


def test_restart_retains_cancel_intent(job_store, tmp_path):
    (tmp_path / "pending.json").write_text(json.dumps({"job_id": "pending", "status": "cancelling",
        "cancel_requested_at": "now", "output_path": str(tmp_path / "absent.json")}))
    loaded = executor._load_analysis_jobs_from_disk()
    assert loaded["pending"]["status"] == "cancelled"
    assert not Path(loaded["pending"]["output_path"]).exists()


@pytest.mark.asyncio
async def test_cancellation_during_preparation_does_not_reach_worker(job_store, tmp_path, monkeypatch):
    entered = asyncio.Event()
    async def prepare(**kwargs):
        entered.set()
        await asyncio.sleep(60)
        pytest.fail("Cancelled preparation continued")
    monkeypatch.setattr(executor, "_prepare_generated_supplementary_for_job", prepare)
    monkeypatch.setattr(executor, "_build_analysis_job_env", lambda kind: {})
    job_store["prep"] = {"job_id": "prep", "status": "queued"}
    task = asyncio.create_task(executor._run_analysis_job(job_id="prep", command=["must-not-run"], output_path=tmp_path / "run.json"))
    await asyncio.wait_for(entered.wait(), 2)
    await executor.cancel_analysis_job("prep")
    await asyncio.wait_for(task, 2)
    assert job_store["prep"]["status"] == "cancelled"
    assert not state.ANALYSIS_JOB_PROCESSES and not state.ANALYSIS_JOB_PREPARATIONS


@pytest.mark.asyncio
async def test_cancelled_reader_and_etag_change_without_rewriting_analysis(job_store, tmp_path):
    from backend.portfolio_read_store import cancellation_view, memo_etag
    from backend.routers.runs import _build_portfolio_read_models
    path = tmp_path / "run.json"
    data = {"analysis_kind": "portfolio_positioning", "workflow_version": 4, "pipeline_status": "running",
        "structured_data": {"analysis_kind": "portfolio_positioning", "asset_class_targets": []},
        "independent_ideal": {"asset_class_targets": [{"asset_class": "cash", "target_pct": 100}]},
        "portfolio_snapshot": {}, "evidence_brief": {}}
    path.write_text(json.dumps(data))
    original, old_etag = path.read_bytes(), memo_etag(path)
    job_store["reader"] = {"job_id": "reader", "status": "queued", "output_path": str(path)}
    await executor.cancel_analysis_job("reader")
    assert cancellation_view(path, data)["pipeline_status"] == "cancelled"
    assert "Analysis stopped" in _build_portfolio_read_models(path, data)["memo"]["structured_data"]["executive_summary"]
    assert path.read_bytes() == original
    assert memo_etag(path) != old_etag
