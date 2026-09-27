"""FastAPI backend for LLM Council."""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import API_DOCS_ENABLED
from .jobs.executor import _load_analysis_jobs_from_disk
from .jobs.state import ANALYSIS_JOBS, ANALYSIS_JOBS_LOCK, PROJECT_ROOT
from .logging_config import configure_logging
from .middleware import auth_middleware
from .routers import analysis_jobs as analysis_jobs_router
from .routers import company_types as company_types_router
from .routers import conversations as conversations_router
from .routers import model_routing as model_routing_router
from .routers import health, memos, misc, scenario_router_routes
from .routers import runs as runs_router
from .routers.conversations import (
    build_enhanced_context,
    build_template_context_for_prompt,
)

logger = logging.getLogger(__name__)

# Re-exported for legacy integration scripts that import these helpers from
# backend.main rather than their router module.
__all__ = ["app", "create_app", "build_enhanced_context", "build_template_context_for_prompt"]


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Configure logging and load persisted analysis jobs at startup."""
    configure_logging()
    health.ensure_runtime_storage()
    loaded = _load_analysis_jobs_from_disk()
    async with ANALYSIS_JOBS_LOCK:
        ANALYSIS_JOBS.clear()
        ANALYSIS_JOBS.update(loaded)
    try:
        # Migrate legacy artifacts once before accepting traffic; later starts read only the index.
        await runs_router.list_portfolio_positioning_runs(limit=1)
    except Exception:
        logger.exception("Unable to warm portfolio read index; direct memo reads remain available")
    await scenario_router_routes.start_scenario_router_event_worker()
    try:
        yield
    finally:
        await scenario_router_routes.stop_scenario_router_event_worker()


_STATIC_DIR = PROJECT_ROOT / "frontend" / "dist"
_SPA_ROUTES: frozenset[str] = frozenset(
    {
        "/",
        "/council",
        "/council/new",
        "/council/runs",
        "/gantt-demo",
        "/gantt-lab",
        "/announcement-router",
        "/scenario-router",
        "/portfolio-analysis",
        "/portfolio-positioning",
        "/portfolio-positioning-memos",
        "/model-routing",
    }
)
_NON_SPA_PREFIXES: tuple[str, ...] = ("/api", "/webhooks")
_NON_SPA_PATHS: frozenset[str] = frozenset(
    {"/healthz", "/readyz", "/docs", "/redoc", "/openapi.json"}
)


def _normalise_path(full_path: str) -> str:
    clean = str(full_path or "").strip("/")
    return f"/{clean}" if clean else "/"


def _is_spa_route(path: str) -> bool:
    if path in _NON_SPA_PATHS:
        return False
    if any(path == prefix or path.startswith(f"{prefix}/") for prefix in _NON_SPA_PREFIXES):
        return False
    return path in _SPA_ROUTES


def create_app(*, api_docs_enabled: Optional[bool] = None) -> FastAPI:
    """Build the application with explicit API-documentation exposure."""
    docs_enabled = API_DOCS_ENABLED if api_docs_enabled is None else bool(api_docs_enabled)
    app = FastAPI(
        title="Alpha Edge Intelligence API",
        lifespan=_lifespan,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)
    app.middleware("http")(auth_middleware)

    app.include_router(health.router)
    app.include_router(misc.router)
    app.include_router(memos.router)
    app.include_router(company_types_router.router)
    app.include_router(conversations_router.router)
    app.include_router(scenario_router_routes.router)
    app.include_router(runs_router.router)
    app.include_router(analysis_jobs_router.router)
    app.include_router(model_routing_router.router)

    # ── Static / SPA fallback ────────────────────────────────────────────────
    if _STATIC_DIR.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_STATIC_DIR / "assets")), name="assets")

        @app.get("/alpha-edge-intelligence.svg", include_in_schema=False)
        async def intelligence_mark():
            mark = _STATIC_DIR / "alpha-edge-intelligence.svg"
            if mark.is_file():
                return FileResponse(str(mark), media_type="image/svg+xml")
            raise HTTPException(status_code=404, detail="Frontend asset not found")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str):
            path = _normalise_path(full_path)
            if not _is_spa_route(path):
                raise HTTPException(status_code=404, detail="Not Found")

            index = _STATIC_DIR / "index.html"
            if index.is_file():
                return FileResponse(str(index))
            raise HTTPException(status_code=404, detail="Frontend not built")

    return app


app = create_app()
