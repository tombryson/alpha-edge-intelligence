import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from backend.jobs import executor, state, submissions
from backend.routers import analysis_jobs


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "JOBS_META_DIR", tmp_path / "meta")
    monkeypatch.setattr(executor, "JOBS_META_DIR", tmp_path / "meta")
    monkeypatch.setattr(executor, "JOBS_OUTPUTS_DIR", tmp_path)
    monkeypatch.setattr(analysis_jobs, "JOBS_OUTPUTS_DIR", tmp_path)
    monkeypatch.setattr(analysis_jobs, "_ensure_system_enabled", lambda: None)
    state.ANALYSIS_JOBS.clear()
    yield tmp_path
    state.ANALYSIS_JOBS.clear()


def test_reservation_is_atomic_and_survives_reopen(isolated):
    key = str(uuid.uuid4())
    def claim(_):
        return submissions.reserve(key, "same", str(uuid.uuid4()))
    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(claim, range(8)))
    assert sum(fresh for _, fresh in rows) == 1
    assert len({job for job, _ in rows}) == 1
    assert submissions.lookup(key, "same") == rows[0][0]
    with pytest.raises(HTTPException) as failure:
        submissions.reserve(key, "different", str(uuid.uuid4()))
    assert failure.value.status_code == 409


def test_duplicate_route_and_restart_never_launch_twice(isolated, monkeypatch):
    launched = []
    async def run(**kwargs):
        launched.append(kwargs["job_id"])
    monkeypatch.setattr(analysis_jobs, "_run_analysis_job", run)
    app = FastAPI()
    app.include_router(analysis_jobs.router)
    key = str(uuid.uuid4())
    headers = {"Idempotency-Key": key}
    payload = {"ticker": "ASX:VMM", "query": "Synthetic test; no provider calls"}
    with TestClient(app) as client:
        first = client.post("/api/analysis-jobs", json=payload, headers=headers)
        assert first.status_code == 202, first.text
        job_id = first.json()["job_id"]
        second = client.post("/api/analysis-jobs", json=payload, headers=headers)
        assert second.json()["job_id"] == job_id
        state.ANALYSIS_JOBS.clear()
        # The normal restart loader marks interrupted jobs failed; it never requeues them.
        state.ANALYSIS_JOBS.update(executor._load_analysis_jobs_from_disk())
        recovered = client.get(f"/api/analysis-submissions/{key}")
        assert recovered.json()["job_id"] == job_id
        assert recovered.json()["status"] == "failed"
        assert client.post("/api/analysis-jobs", json=payload, headers=headers).json()["job_id"] == job_id
        assert client.post("/api/analysis-jobs", json={**payload, "query": "changed"}, headers=headers).status_code == 409
    assert launched == [job_id]


def test_crash_after_claim_is_visible_not_reexecuted(isolated):
    key = str(uuid.uuid4())
    submissions.reserve(key, "payload", str(uuid.uuid4()))
    result = asyncio.run(analysis_jobs.get_analysis_submission(key))
    assert result["submission_status"] == "uncertain"
    assert "job_id" not in result


def test_failed_funding_preflight_does_not_reserve_or_launch(isolated, monkeypatch):
    async def unavailable(_context, _previous):
        return {"status": "unavailable", "message": "Funding check unavailable"}

    monkeypatch.setattr(analysis_jobs, "_portfolio_preflight", unavailable)
    monkeypatch.setattr(analysis_jobs, "get_portfolio_allocator_assignments", lambda: {})
    app = FastAPI()
    app.include_router(analysis_jobs.router)
    key = str(uuid.uuid4())
    with TestClient(app) as client:
        response = client.post("/api/analysis-jobs", headers={"Idempotency-Key": key}, json={
            "job_type": "portfolio_positioning", "portfolio_context": {"portfolio_value": 1000},
        })
    assert response.status_code == 503, response.text
    assert response.json()["detail"]["submission_status"] == "not_submitted"
    assert submissions.lookup(key) is None
    assert not state.ANALYSIS_JOBS


@pytest.mark.asyncio
async def test_fingerprint_is_order_independent_and_includes_uploaded_bytes(isolated):
    from io import BytesIO

    from starlette.datastructures import UploadFile
    assert await submissions.fingerprint({"a": 1, "b": 2}) == await submissions.fingerprint({"b": 2, "a": 1})
    one = UploadFile(BytesIO(b"one"), filename="source.txt")
    two = UploadFile(BytesIO(b"two"), filename="source.txt")
    assert await submissions.fingerprint({}, one) != await submissions.fingerprint({}, two)
    assert await one.read() == b"one"
