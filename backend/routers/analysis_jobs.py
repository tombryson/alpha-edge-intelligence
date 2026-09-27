"""HTTP routes for long-running analysis jobs.

Handles job creation, status polling, streaming log output, result
retrieval, and admin endpoints.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from ..jobs.executor import (
    ANALYSIS_JOB_HEARTBEAT_SECONDS,
    CreateAnalysisJobRequest,
    _build_analysis_job_command,
    _build_job_run_filename,
    _build_synthetic_job_record_from_run,
    _coerce_form_bool,
    _ensure_analysis_job_dirs,
    _persist_job_record,
    _public_job_view,
    _run_analysis_job,
    cancel_analysis_job,
    _run_id_from_synthetic_job_id,
    _sanitize_analysis_request_payload,
    _store_portfolio_context_for_job,
    _store_supplementary_upload_for_job,
    _utc_now_iso,
    _validate_job_type,
    _validate_portfolio_positioning_mode,
    _validate_supplementary_mode,
)
from ..jobs.structured import _build_integration_packet
from ..jobs.state import (
    ANALYSIS_JOBS,
    ANALYSIS_JOBS_LOCK,
    INSTANCE_ID,
    JOBS_OUTPUTS_DIR,
    PORTFOLIO_POSITIONING_OUTPUTS_DIR,
)
from ..utils import _ensure_system_enabled
from ..model_routing import get_portfolio_allocator_assignments, runtime_model_environment
from ..portfolio_funding import preflight
from .runs import get_gantt_run, get_portfolio_positioning_run, list_gantt_runs
from ..jobs import submissions

router = APIRouter()
logger = logging.getLogger(__name__)
_FUNDING_SUBMISSION_LOCK = asyncio.Lock()


async def _serialize_submissions():
    # Keep the balance check and job registration together across concurrent starts.
    async with _FUNDING_SUBMISSION_LOCK:
        yield


async def _portfolio_preflight(context, previous=None):
    async with ANALYSIS_JOBS_LOCK:
        reserved = sum((job.get("funding") or {}).get("estimate", {}).get("high_usd", 0)
            for job in ANALYSIS_JOBS.values() if job.get("status") in {"queued", "running", "cancelling"})
    return await preflight(context, {**os.environ, **runtime_model_environment()}, previous, reserved)


async def _portfolio_source(payload):
    if payload.preserve_portfolio_baselines and not payload.reassess_portfolio_run_id:
        raise HTTPException(status_code=422, detail="Preserving baselines requires a source run for a new assessment")
    if payload.resume_portfolio_run_id and payload.reassess_portfolio_run_id:
        raise HTTPException(status_code=422, detail="Choose recovery or a new assessment, not both")
    run_id = payload.resume_portfolio_run_id or payload.reassess_portfolio_run_id
    if payload.resume_portfolio_run_id and payload.investment_plays is not None:
        raise HTTPException(status_code=422, detail="Recovery preserves the original plays. Start a new assessment to change them.")
    if not run_id:
        if payload.investment_plays is not None:
            from ..portfolio_independent import normalize_plays
            try:
                payload.portfolio_context = {**(payload.portfolio_context or {}),
                    "investment_plays": normalize_plays(payload.investment_plays)}
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        return None
    from ..jobs.runs import _resolve_portfolio_positioning_artifact_path
    path = _resolve_portfolio_positioning_artifact_path(Path(run_id).name)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Portfolio run not found")
    previous = await asyncio.to_thread(lambda: json.loads(path.read_text()))
    context = dict(previous.get("portfolio_context") or previous.get("portfolio_snapshot") or {})
    context.pop("repair_preserve_baselines", None)
    if payload.resume_portfolio_run_id or previous.get("workflow_version") in (3, 4):
        context.update(frozen_research_query=previous.get("query"),
                       frozen_company_evidence=(previous.get("portfolio_snapshot") or {}).get("company_evidence"))
    if payload.reassess_portfolio_run_id:
        from ..portfolio_independent import normalize_plays
        try:
            context["investment_plays"] = normalize_plays(payload.investment_plays if payload.investment_plays is not None
                                                        else context.get("investment_plays"))
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        context["source_run_id"] = Path(run_id).name
        if payload.preserve_portfolio_baselines:
            context["repair_preserve_baselines"] = True
            checkpoint = path.with_suffix(".checkpoint.json")
            if previous.get("workflow_version") not in (3, 4) or not checkpoint.is_file():
                raise HTTPException(status_code=409, detail="Baseline-preserving repair requires the original independent-workflow checkpoint")
            from ..portfolio_repair import load_frozen_baselines
            try:
                await asyncio.to_thread(load_frozen_baselines, context, checkpoint)
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
    payload.portfolio_context = context
    payload.query = previous.get("query") or payload.query
    payload.run_label = "portfolio_ideas_review" if payload.reassess_portfolio_run_id else "portfolio_recovery"
    return previous


@router.post("/api/portfolio-positioning/preflight")
async def portfolio_preflight(payload: CreateAnalysisJobRequest):
    previous = await _portfolio_source(payload)
    return await _portfolio_preflight(payload.portfolio_context or {}, previous if payload.resume_portfolio_run_id else None)

@router.post("/api/analysis-jobs", status_code=202, dependencies=[Depends(_serialize_submissions)])
async def create_analysis_job(
    request: Request,
    job_type: Optional[str] = Form(None),
    query: Optional[str] = Form(None),
    ticker: Optional[str] = Form(None),
    company_name: Optional[str] = Form(None),
    template_id: Optional[str] = Form(None),
    company_type: Optional[str] = Form(None),
    exchange: Optional[str] = Form(None),
    stage1_only: Optional[str] = Form(None),
    stage2_revision_pass: Optional[str] = Form(None),
    secondary_chairman_model: Optional[str] = Form(None),
    run_label: Optional[str] = Form(None),
    diagnostic_mode: Optional[str] = Form(None),
    reuse_recent_bundle: Optional[str] = Form(None),
    reuse_supplementary_from_job_id: Optional[str] = Form(None),
    supplementary_mode: Optional[str] = Form(None),
    portfolio_positioning_mode: Optional[str] = Form(None),
    supplementary_file: UploadFile = File(None),
):
    """
    Submit an async full-analysis job.
    Produces a run artifact under outputs/jobs/ and returns a stable job_id.
    """
    _ensure_system_enabled()
    content_type = str(request.headers.get("content-type") or "").lower()
    if "multipart/form-data" in content_type:
        job_request = CreateAnalysisJobRequest(
            job_type=job_type,
            query=query,
            ticker=ticker,
            company_name=company_name,
            template_id=template_id,
            company_type=company_type,
            exchange=exchange,
            stage1_only=_coerce_form_bool(stage1_only, default=False),
            stage2_revision_pass=str(stage2_revision_pass or "on"),
            secondary_chairman_model=secondary_chairman_model,
            run_label=run_label,
            diagnostic_mode=_coerce_form_bool(diagnostic_mode, default=False),
            reuse_recent_bundle=_coerce_form_bool(reuse_recent_bundle, default=False),
            reuse_supplementary_from_job_id=str(reuse_supplementary_from_job_id or "").strip() or None,
            supplementary_mode=_validate_supplementary_mode(supplementary_mode),
            portfolio_positioning_mode=_validate_portfolio_positioning_mode(portfolio_positioning_mode),
        )
    else:
        try:
            body = await request.json()
        except Exception:
            body = {}
        job_request = CreateAnalysisJobRequest(**(body or {}))
        supplementary_file = None

    key = submissions.submission_id(request.headers.get("Idempotency-Key"))
    digest = await submissions.fingerprint(job_request.model_dump(), supplementary_file) if key else None
    if key:
        existing_id = submissions.lookup(key, digest)
        if existing_id:
            return await _submission_view(key, existing_id)

    job_kind = _validate_job_type(job_request.job_type)
    funding = None
    previous = None
    if job_kind == "portfolio_positioning":
        previous = await _portfolio_source(job_request)
        if not isinstance(job_request.portfolio_context, dict) or not job_request.portfolio_context:
            raise HTTPException(
                status_code=400,
                detail="Portfolio positioning requires portfolio_context",
            )
        job_request.portfolio_positioning_mode = _validate_portfolio_positioning_mode(
            job_request.portfolio_positioning_mode
        )
        try:
            json.dumps(job_request.portfolio_context, allow_nan=False)
            from ..portfolio_independent import normalize_plays
            if "investment_plays" in job_request.portfolio_context:
                job_request.portfolio_context["investment_plays"] = normalize_plays(job_request.portfolio_context["investment_plays"])
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=422, detail=f"Invalid portfolio context: {exc}") from exc
        try:
            get_portfolio_allocator_assignments()
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        funding = await _portfolio_preflight(job_request.portfolio_context, previous if job_request.resume_portfolio_run_id else None)
        if funding["status"] != "ready":
            raise HTTPException(status_code=402 if funding["status"] == "insufficient" else 503,
                                detail={"message": funding["message"], "funding": funding,
                                        "code": "COUNCIL_PREFLIGHT_REJECTED", "submission_status": "not_submitted"})
    elif not str(job_request.query or "").strip() and not str(job_request.ticker or "").strip():
        raise HTTPException(
            status_code=400,
            detail="Provide at least one of: query, ticker",
        )

    from ..template_loader import get_template_loader
    loader = get_template_loader()
    requested_exchange = str(job_request.exchange or "").strip()
    requested_ticker = str(job_request.ticker or "").strip().upper()
    if job_kind != "portfolio_positioning" and requested_exchange and not loader.normalize_exchange(requested_exchange):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid exchange value: {requested_exchange}",
        )
    if job_kind != "portfolio_positioning" and requested_ticker and ":" not in requested_ticker and not requested_exchange:
        raise HTTPException(
            status_code=400,
            detail="Ticker must include an exchange prefix (e.g. ASX:BHM) or provide a valid exchange.",
        )

    _ensure_analysis_job_dirs()
    output_name = _build_job_run_filename(job_request)
    output_path = (
        PORTFOLIO_POSITIONING_OUTPUTS_DIR / output_name
        if job_kind == "portfolio_positioning"
        else JOBS_OUTPUTS_DIR / output_name
    )
    job_id = str(uuid.uuid4())
    if key:
        job_id, fresh = submissions.reserve(key, digest, job_id)
        if not fresh:
            return await _submission_view(key, job_id)
    supplementary_upload_path: Optional[Path] = None
    portfolio_context_path: Optional[Path] = None
    supplementary_filename = ""
    if supplementary_file is not None:
        supplementary_upload_path, supplementary_filename = await _store_supplementary_upload_for_job(
            supplementary_file,
            job_id=job_id,
        )
    elif job_request.reuse_supplementary_from_job_id:
        prev_job_id = str(job_request.reuse_supplementary_from_job_id or "").strip()
        if prev_job_id:
            supplementary_dir = JOBS_OUTPUTS_DIR / "supplementary"
            matches = sorted(supplementary_dir.glob(f"{prev_job_id}_*"))
            if not matches:
                raise HTTPException(
                    status_code=404,
                    detail=f"No saved supplementary file found for job: {prev_job_id}",
                )
            supplementary_upload_path = matches[0]
            supplementary_filename = supplementary_upload_path.name

    if job_kind == "portfolio_positioning":
        portfolio_context_path = _store_portfolio_context_for_job(
            job_request.portfolio_context,
            job_id=job_id,
        )
        if portfolio_context_path is None:
            raise HTTPException(status_code=400, detail="Failed to persist portfolio_context")

    command = _build_analysis_job_command(
        job_request,
        output_path,
        supplementary_context_path=supplementary_upload_path,
        portfolio_context_path=portfolio_context_path,
    )
    request_payload = (
        job_request.model_dump()
        if hasattr(job_request, "model_dump")
        else job_request.dict()
    )
    request_payload = _sanitize_analysis_request_payload(request_payload)
    if supplementary_upload_path is not None:
        request_payload["supplementary_file"] = supplementary_filename or "supplementary_document"
    job_record = {
        "job_id": job_id,
        "submission_id": key,
        "status": "queued",
        "stage": "queued",
        "stage_message": "Queued",
        "progress_pct": 0,
        "instance_id": INSTANCE_ID,
        "created_at": _utc_now_iso(),
        "started_at": "",
        "finished_at": "",
        "last_output_at": "",
        "output_path": str(output_path),
        "returncode": None,
        "pid": None,
        "run_id": "",
        "error": "",
        "stdout_tail": "",
        "stderr_tail": "",
        "request": request_payload,
        "command": command,
        "funding": funding,
    }

    async with ANALYSIS_JOBS_LOCK:
        _persist_job_record(job_record)
        ANALYSIS_JOBS[job_id] = job_record

    asyncio.create_task(
        _run_analysis_job(
            job_id=job_id,
            command=command,
            output_path=output_path,
            request_payload=request_payload,
            cleanup_paths=[
                path
                for path in [supplementary_upload_path, portfolio_context_path]
                if path is not None
            ],
        )
    )
    return _public_job_view(job_record)


@router.get("/api/analysis-jobs")
async def list_analysis_jobs(limit: int = 20, job_type: Optional[str] = None):
    """List most recent async analysis jobs."""
    async with ANALYSIS_JOBS_LOCK:
        rows = list(ANALYSIS_JOBS.values())
    if job_type:
        rows = [row for row in rows if (row.get("request") or {}).get("job_type") == job_type]
        rows.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return {"jobs": [_public_job_view(row) for row in rows[: max(1, int(limit))]]}
    run_ids_with_jobs = {
        Path(str(row.get("run_id") or "")).name
        for row in rows
        if str(row.get("run_id") or "").strip()
    }
    try:
        gantt_payload = await list_gantt_runs(limit=max(50, max(1, int(limit)) * 3))
        for run in list(gantt_payload.get("runs") or []):
            run_id = Path(str(run.get("id") or "")).name
            if not run_id or run_id in run_ids_with_jobs:
                continue
            rows.append(_build_synthetic_job_record_from_run(run))
    except Exception:
        pass
    rows.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    return {"jobs": [_public_job_view(row) for row in rows[: max(1, int(limit))]]}


async def _submission_view(key, job_id):
    async with ANALYSIS_JOBS_LOCK:
        job = ANALYSIS_JOBS.get(job_id)
    if job is None:
        job = submissions.read_job(job_id)
    if job is not None:
        return _public_job_view(job)
    # A crash between reservation and job publication is not permission to run twice.
    return {"submission_id": key, "submission_status": "uncertain",
            "code": "COUNCIL_SUBMISSION_UNCERTAIN",
            "detail": "Submission reserved, but its job is not available. Review in Intelligence before starting another run."}


@router.get("/api/analysis-submissions/{key}")
async def get_analysis_submission(key: str):
    key = submissions.submission_id(key)
    job_id = submissions.lookup(key)
    if not job_id:
        raise HTTPException(404, detail="Submission not found; do not assume the original request has finished")
    return await _submission_view(key, job_id)


@router.get("/api/analysis-jobs/{job_id}")
async def get_analysis_job(job_id: str):
    """Fetch status/log tails for one async analysis job."""
    async with ANALYSIS_JOBS_LOCK:
        job = ANALYSIS_JOBS.get(str(job_id))
    if isinstance(job, dict):
        return _public_job_view(job)

    synthetic_run_id = _run_id_from_synthetic_job_id(job_id)
    if synthetic_run_id:
        run_payload = await get_gantt_run(synthetic_run_id)
        run_meta = {
            "id": run_payload.get("id") or synthetic_run_id,
            "label": run_payload.get("label") or synthetic_run_id,
            "ticker": ((run_payload.get("structured_data") or {}).get("ticker") if isinstance(run_payload.get("structured_data"), dict) else ""),
            "company_name": ((run_payload.get("structured_data") or {}).get("company_name") if isinstance(run_payload.get("structured_data"), dict) else ""),
            "analysis_date": ((run_payload.get("structured_data") or {}).get("analysis_date") if isinstance(run_payload.get("structured_data"), dict) else ""),
            "updated_at": run_payload.get("updated_at") or "",
        }
        return _public_job_view(_build_synthetic_job_record_from_run(run_meta))

    raise HTTPException(
        status_code=404,
        detail={
            "message": "Analysis job not found on this instance",
            "instance_id": INSTANCE_ID,
        },
    )


@router.post("/api/analysis-jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    return _public_job_view(await cancel_analysis_job(job_id))


@router.get("/api/analysis-jobs/{job_id}/result")
async def get_analysis_job_result(job_id: str):
    """Return normalized run payload once the async analysis job succeeds."""
    async with ANALYSIS_JOBS_LOCK:
        job = ANALYSIS_JOBS.get(str(job_id))
    synthetic_run_id = _run_id_from_synthetic_job_id(job_id)
    if not isinstance(job, dict):
        if not synthetic_run_id:
            raise HTTPException(status_code=404, detail="Analysis job not found")
        run_payload = await get_gantt_run(synthetic_run_id)
        structured = run_payload.get("structured_data") if isinstance(run_payload.get("structured_data"), dict) else {}
        synthetic_job = _build_synthetic_job_record_from_run(
            {
                "id": run_payload.get("id") or synthetic_run_id,
                "label": run_payload.get("label") or synthetic_run_id,
                "ticker": structured.get("ticker") or "",
                "company_name": structured.get("company_name") or structured.get("company") or "",
                "analysis_date": structured.get("analysis_date") or "",
                "updated_at": run_payload.get("updated_at") or "",
            }
        )
        report_packet = _build_integration_packet(run_id=synthetic_run_id, run_payload=run_payload)
        return {
            "job": _public_job_view(synthetic_job),
            "run": run_payload,
            "report_packet": report_packet,
        }

    status = str(job.get("status") or "")
    run_id = str(job.get("run_id") or "")
    partial_portfolio = status == "failed" and run_id and str((job.get("request") or {}).get("job_type") or "") == "portfolio_positioning"
    if status == "failed" and not partial_portfolio:
        raise HTTPException(
            status_code=409,
            detail=str(job.get("error") or "Analysis job failed"),
        )
    if (status != "succeeded" and not partial_portfolio) or not run_id:
        raise HTTPException(status_code=409, detail=f"Analysis job not completed (status={status})")

    if str((job.get("request") or {}).get("job_type") or "").strip().lower() == "portfolio_positioning":
        run_payload = await get_portfolio_positioning_run(run_id)
        return {
            "job": _public_job_view(job),
            "run": run_payload,
            "report_packet": None,
        }

    run_payload = await get_gantt_run(run_id)
    report_packet = _build_integration_packet(run_id=run_id, run_payload=run_payload)
    return {
        "job": _public_job_view(job),
        "run": run_payload,
        "report_packet": report_packet,
    }


@router.get("/api/analysis-jobs/{job_id}/events")
async def stream_analysis_job_events(job_id: str, poll_ms: int = 1000):
    """
    Stream async job status updates (SSE) for progress bars and live UX feedback.
    Emits `analysis_job` events when status/stage/progress changes and exits on terminal state.
    """
    interval_s = max(0.25, min(5.0, float(poll_ms) / 1000.0))

    async def _event_stream():
        last_signature: Optional[Tuple[Any, ...]] = None
        while True:
            async with ANALYSIS_JOBS_LOCK:
                job = ANALYSIS_JOBS.get(str(job_id))
                payload = _public_job_view(job) if isinstance(job, dict) else None

            if payload is None:
                data = {
                    "type": "analysis_job_not_found",
                    "job_id": str(job_id),
                    "instance_id": INSTANCE_ID,
                }
                yield f"event: error\ndata: {json.dumps(data)}\n\n"
                break

            signature = (
                payload.get("status"),
                payload.get("stage"),
                payload.get("progress_pct"),
                payload.get("stage_message"),
                payload.get("last_output_at"),
                payload.get("heartbeat_at"),
                payload.get("heartbeat_count"),
                (payload.get("execution_progress") or {}).get("revision"),
                payload.get("run_id"),
                payload.get("error"),
            )
            if signature != last_signature:
                yield f"event: analysis_job\ndata: {json.dumps(payload)}\n\n"
                last_signature = signature

            status = str(payload.get("status") or "").lower()
            if status in {"succeeded", "failed", "cancelled"}:
                break
            await asyncio.sleep(interval_s)

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
