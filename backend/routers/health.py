"""Public health probes and an authenticated session check."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..jobs.state import JOBS_META_DIR, JOBS_OUTPUTS_DIR, OUTPUTS_DIR

router = APIRouter()

_SERVICE_NAME = "alpha-edge-intelligence"
_REQUIRED_STORAGE_PATHS: tuple[tuple[str, Path], ...] = (
    ("outputs", OUTPUTS_DIR),
    ("jobs", JOBS_OUTPUTS_DIR),
    ("job metadata", JOBS_META_DIR),
)


def ensure_runtime_storage() -> None:
    """Create the persisted runtime directories during application startup."""
    for _label, directory in _REQUIRED_STORAGE_PATHS:
        directory.mkdir(parents=True, exist_ok=True)


def _storage_readiness_issues() -> list[str]:
    """Return storage issues without exposing filesystem details to callers."""
    issues: list[str] = []
    for label, directory in _REQUIRED_STORAGE_PATHS:
        if not directory.is_dir():
            issues.append(f"{label} directory is unavailable")
            continue
        if not os.access(directory, os.R_OK | os.W_OK):
            issues.append(f"{label} directory is not readable and writable")
    return issues


def _health_payload() -> dict[str, str]:
    return {"status": "ok", "service": _SERVICE_NAME}


@router.get("/healthz", include_in_schema=False)
async def healthz():
    """Report only whether the running process can answer HTTP."""
    return _health_payload()


@router.get("/readyz", include_in_schema=False)
async def readyz():
    """Report whether the runtime storage required for ordinary work is usable."""
    if _storage_readiness_issues():
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "service": _SERVICE_NAME},
        )
    return {"status": "ready", "service": _SERVICE_NAME}


@router.get("/api/health", include_in_schema=False)
async def legacy_api_health():
    """Compatibility liveness endpoint for existing monitors."""
    return _health_payload()


@router.get("/api/auth/status", include_in_schema=False)
async def auth_status():
    """The existing /api/ middleware verifies access before reaching this route."""
    return JSONResponse(content={"authenticated": True}, headers={"Cache-Control": "no-store"})
