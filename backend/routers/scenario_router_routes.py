"""Scenario-router HTTP routes.

Handles inbound event announcements, webhook verification, deduplication,
model-adjudication, and scenario-routing decisions.
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..config import (
    OPENROUTER_API_KEY,
    SCENARIO_ROUTER_MODEL_ADJUDICATION_ENABLED,
    SCENARIO_ROUTER_MODEL_ADJUDICATION_MAX_CASES,
    SCENARIO_ROUTER_QUEUE_MAX_ATTEMPTS,
    SCENARIO_ROUTER_QUEUE_PROCESS_TIMEOUT_SECONDS,
    SCENARIO_ROUTER_QUEUE_RETRY_DELAY_SECONDS,
    SCENARIO_ROUTER_THESIS_JUDGE_ENABLED,
    SCENARIO_ROUTER_WEBHOOK_REQUIRE_SECRET,
    SCENARIO_ROUTER_WEBHOOK_SECRET,
)
from ..jobs.state import (
    LEGACY_FRESHNESS_DEDUPE_DIR,
    SCENARIO_ROUTER_DEDUPE_DIR,
    SCENARIO_ROUTER_QUEUE_DIR,
)
from ..scenario_router.event_queue import ScenarioRouterEventQueue

router = APIRouter()
logger = logging.getLogger(__name__)
SCENARIO_ROUTER_EVENT_QUEUE = ScenarioRouterEventQueue(
    SCENARIO_ROUTER_QUEUE_DIR,
    process_timeout_seconds=SCENARIO_ROUTER_QUEUE_PROCESS_TIMEOUT_SECONDS,
    max_attempts=SCENARIO_ROUTER_QUEUE_MAX_ATTEMPTS,
    retry_delay_seconds=SCENARIO_ROUTER_QUEUE_RETRY_DELAY_SECONDS,
)

def _build_scenario_router_service():
    import asyncio
    from ..scenario_router.observability import ScenarioRouterObservability
    from ..scenario_router.document_reader import DocumentReader
    from ..scenario_router.lab_scribe import LabScribe
    from ..scenario_router.market_facts_resolver import ScenarioMarketFactsResolver
    from ..scenario_router.model_thesis_judge import ModelAnnouncementThesisJudge
    from ..scenario_router.run_selector import LatestRunSelector
    from ..scenario_router.semantic_adjudicator import ModelSemanticAdjudicator
    from ..scenario_router.service import (
        ScenarioRouterDependencies,
        ScenarioRouterService,
    )
    from ..scenario_router.source_resolver import SourceResolver
    from ..scenario_router.thesis_comparator import ThesisComparator
    model_adjudicator = (
        ModelSemanticAdjudicator().adjudicate
        if SCENARIO_ROUTER_MODEL_ADJUDICATION_ENABLED and OPENROUTER_API_KEY
        else None
    )
    thesis_comparator = ThesisComparator(
        semantic_adjudicator=model_adjudicator,
        max_semantic_adjudications=SCENARIO_ROUTER_MODEL_ADJUDICATION_MAX_CASES,
    )
    async def load_evidence(facts, baseline_run):
        return await asyncio.to_thread(ScenarioRouterObservability().catalyst_context, facts, baseline_run)

    announcement_interpreter = (
        ModelAnnouncementThesisJudge(evidence_loader=load_evidence).interpret
        if SCENARIO_ROUTER_THESIS_JUDGE_ENABLED and OPENROUTER_API_KEY
        else ModelAnnouncementThesisJudge(model="").interpret
    )

    return ScenarioRouterService(
        ScenarioRouterDependencies(
            source_resolver=SourceResolver().resolve,
            document_reader=DocumentReader().read,
            run_selector=LatestRunSelector(limit=25).select_latest,
            announcement_interpreter=announcement_interpreter,
            market_facts_resolver=ScenarioMarketFactsResolver().resolve,
            thesis_comparator=thesis_comparator.compare_async if model_adjudicator else thesis_comparator.compare,
            lab_scribe=LabScribe().persist,
        )
    )


def _safe_scenario_router_key(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _scenario_router_dedupe_paths(event_key: str) -> Tuple[Path, Path]:
    safe_key = _safe_scenario_router_key(event_key)
    if not safe_key:
        return Path(""), Path("")
    prefix = safe_key[:2]
    directory = SCENARIO_ROUTER_DEDUPE_DIR / prefix
    return directory, directory / f"{safe_key}.json"


def _load_scenario_router_dedupe(event_key: str) -> Dict[str, Any]:
    directory, marker_path = _scenario_router_dedupe_paths(event_key)
    if not directory:
        return {}
    if not marker_path.exists():
        legacy_path = LEGACY_FRESHNESS_DEDUPE_DIR / marker_path.parent.name / marker_path.name
        if legacy_path.exists():
            marker_path = legacy_path
        else:
            return {}
    try:
        return json.loads(marker_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _persist_scenario_router_dedupe(event_key: str, payload: Dict[str, Any]) -> None:
    directory, marker_path = _scenario_router_dedupe_paths(event_key)
    if not directory:
        return
    directory.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )


def _choose_scenario_router_event_key(payload: Dict[str, Any]) -> str:
    for field in ("gmail_message_id", "event_id", "message_id"):
        value = str(payload.get(field) or "").strip()
        if value:
            return value
    subject = str(payload.get("subject") or "").strip()
    sender = str(payload.get("sender") or "").strip().lower()
    received_at = str(payload.get("received_at_utc") or "").strip()
    ticker = str(payload.get("ticker") or "").strip().upper()
    if subject or sender or received_at:
        return f"{ticker}|{sender}|{received_at}|{subject}"
    return ""


def _check_scenario_router_webhook_secret(request: Request) -> None:
    provided = str(
        request.headers.get("x-scenario-router-secret")
        or request.headers.get("x-freshness-secret")
        or ""
    ).strip()
    configured = str(SCENARIO_ROUTER_WEBHOOK_SECRET or "").strip()
    if not configured and not SCENARIO_ROUTER_WEBHOOK_REQUIRE_SECRET:
        return
    if not configured:
        raise HTTPException(
            status_code=503,
            detail="Scenario router webhook secret is required but not configured.",
        )
    if not provided or not hmac.compare_digest(provided, configured):
        raise HTTPException(status_code=401, detail="Invalid scenario router webhook secret.")



class ScenarioRouterAttachmentPayload(BaseModel):
    filename: str
    content_type: Optional[str] = None
    local_path: Optional[str] = None


class ProcessScenarioRouterAnnouncementRequest(BaseModel):
    event_id: Optional[str] = None
    gmail_message_id: Optional[str] = None
    message_id: Optional[str] = None
    ticker: Optional[str] = None
    exchange: Optional[str] = None
    company_hint: Optional[str] = None
    company_name: Optional[str] = None
    subject: Optional[str] = None
    sender: Optional[str] = None
    body_text: Optional[str] = None
    source_channel: Optional[str] = None
    received_at_utc: Optional[str] = None
    urls: List[str] = []
    attachments: List[ScenarioRouterAttachmentPayload] = []

@router.get("/api/announcement-router/overview")
@router.get("/api/scenario-router/overview")
async def get_scenario_router_overview(limit: int = 100, ticker: str = ""):
    from ..scenario_router.observability import ScenarioRouterObservability

    observer = ScenarioRouterObservability()
    return observer.build_overview(recent_limit=max(1, min(int(limit or 100), 5000)), ticker=str(ticker or "").strip())


@router.get("/api/announcement-router/events")
@router.get("/api/scenario-router/events")
async def list_scenario_router_events(limit: int = 50, ticker: str = ""):
    from ..scenario_router.observability import ScenarioRouterObservability

    observer = ScenarioRouterObservability()
    return {
        "events": observer.list_recent_events(limit=max(1, min(int(limit or 50), 5000)), ticker=str(ticker or "").strip()),
    }


@router.get("/api/announcement-router/signal")
@router.get("/api/announcement-router/signals")
@router.get("/api/scenario-router/signal")
@router.get("/api/scenario-router/signals")
async def get_scenario_router_signals(limit: int = 500, ticker: str = ""):
    from ..scenario_router.observability import ScenarioRouterObservability

    observer = ScenarioRouterObservability()
    return observer.build_signal_map(limit=max(1, min(int(limit or 500), 5000)), ticker=str(ticker or "").strip())


@router.get("/api/market-path/security-history/{ticker:path}")
async def get_market_path_security_history(ticker: str):
    from ..price_history_bridge import fetch_alpha_edge_security_history

    return await fetch_alpha_edge_security_history(str(ticker or "").strip())


@router.post("/api/announcement-router/reviews/{event_id}")
@router.post("/api/scenario-router/reviews/{event_id}")
async def post_scenario_router_review(event_id: str, payload: Dict[str, Any]):
    from ..scenario_router.review_store import save_review

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload must be a JSON object")
    try:
        review = save_review(
            event_id,
            status=str(payload.get("review_status") or payload.get("status") or "").strip(),
            note=str(payload.get("review_note") or payload.get("note") or "").strip(),
            actor=str(payload.get("reviewed_by") or payload.get("actor") or "analyst").strip() or "analyst",
            owner=str(payload.get("review_owner") or payload.get("owner") or "").strip(),
            router_override=payload.get("router_override") if isinstance(payload.get("router_override"), dict) else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok", "review": review}


@router.post("/api/announcement-router/reassess/{event_id}")
@router.post("/api/scenario-router/reassess/{event_id}")
async def post_scenario_router_reassess(event_id: str):
    """Rerun the model thesis judge for one stored router event."""
    from ..scenario_router.lab_scribe import SCENARIO_ROUTER_EVENTS_DIR
    from ..scenario_router.observability import ScenarioRouterObservability
    from ..scenario_router.rejudge_artifacts import rejudge_payload
    from ..scenario_router.review_store import apply_review_overlay, load_review

    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=503, detail="OpenRouter API key is not configured; AI reassessment is unavailable.")

    clean_event_id = str(event_id or "").strip()
    if not clean_event_id:
        raise HTTPException(status_code=400, detail="event_id is required")

    matches = _scenario_router_artifact_paths_for_event(clean_event_id, SCENARIO_ROUTER_EVENTS_DIR)
    primary_path = _choose_primary_scenario_router_artifact(matches)
    if primary_path is None:
        raise HTTPException(status_code=404, detail=f"No stored router artifact found for event_id={clean_event_id}")

    try:
        payload = json.loads(primary_path.read_text(encoding="utf-8"))
        updated = await rejudge_payload(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AI reassessment failed: {exc}") from exc

    judgement = (updated.get("announcement_facts") or {}).get("model_judgement") or {}
    if judgement.get("status") != "valid":
        from ..scenario_router.model_thesis_judge import thesis_judge_failure_message

        raise HTTPException(status_code=502, detail=thesis_judge_failure_message(str(judgement.get("reason") or "")))

    serialized = json.dumps(updated, indent=2, ensure_ascii=True)
    written_paths: List[str] = []
    for path in matches:
        try:
            path.write_text(serialized, encoding="utf-8")
            written_paths.append(str(path))
        except Exception:
            logger.warning("Failed to rewrite reassessed router artifact: %s", path, exc_info=True)

    observer = ScenarioRouterObservability()
    row = observer._summarize_event_payload(updated, path=primary_path)
    row = apply_review_overlay(row, load_review(str(row.get("event_id") or clean_event_id)))
    return {
        "status": "ok",
        "event_id": clean_event_id,
        "rewritten": len(written_paths),
        "rewritten_paths": written_paths[:20],
        "row": row,
    }


def _scenario_router_artifact_paths_for_event(event_id: str, base_dir: Path) -> List[Path]:
    clean_event_id = str(event_id or "").strip()
    if not clean_event_id:
        return []
    base = Path(base_dir)
    if not base.exists() or not base.is_dir():
        return []
    matches: List[Path] = []
    for path in base.rglob("*.json"):
        parts = set(path.parts)
        if "reviews" in parts or "dedupe" in parts:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        event = payload.get("event") if isinstance(payload.get("event"), dict) else {}
        packet = payload.get("announcement_packet") if isinstance(payload.get("announcement_packet"), dict) else {}
        candidate = str(event.get("event_id") or packet.get("event_id") or payload.get("event_id") or "").strip()
        if candidate == clean_event_id:
            matches.append(path)
    return matches


def _choose_primary_scenario_router_artifact(paths: List[Path]) -> Optional[Path]:
    if not paths:
        return None
    def rank(path: Path) -> Tuple[int, float]:
        parts = set(path.parts)
        is_latest = path.name == "latest.json"
        is_by_run = "by_run" in parts
        return (10 if is_latest else 0) + (5 if is_by_run else 0), -path.stat().st_mtime
    return sorted(paths, key=rank)[0]


@router.get("/api/announcement-router/evaluations")
@router.get("/api/scenario-router/evaluations")
async def get_scenario_router_evaluations():
    from ..scenario_router.observability import ScenarioRouterObservability

    observer = ScenarioRouterObservability()
    return observer.run_evaluation_suite()


@router.post("/api/announcement-router/mock-evaluate")
@router.post("/api/scenario-router/mock-evaluate")
async def post_scenario_router_mock_evaluate(payload: Dict[str, Any]):
    """Run mock announcement(s) against supplied mock thesis map(s).

    This is deterministic and non-persistent: no source fetch, no LLM call, no
    artifact write. It is intended for thesis-by-thesis router regression tests
    and manual QA.
    """
    from ..scenario_router.mock_harness import run_mock_router_case, run_mock_router_cases

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload must be a JSON object")
    cases = payload.get("cases")
    try:
        if isinstance(cases, list):
            return run_mock_router_cases([case for case in cases if isinstance(case, dict)])
        return run_mock_router_case(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Mock router evaluation failed: {exc}") from exc


@router.post("/api/announcement-router/process-announcement")
@router.post("/api/scenario-router/process-announcement")
@router.post("/api/freshness/process-announcement")
async def process_scenario_router_announcement(
    request: ProcessScenarioRouterAnnouncementRequest,
    raw_request: Request,
):
    """Process one inbound announcement event against the latest saved lab run."""
    _check_scenario_router_webhook_secret(raw_request)
    return await _process_scenario_router_payload(request.model_dump())


def _scenario_router_duplicate_response(
    *,
    existing: Dict[str, Any],
    payload: Dict[str, Any],
    dedupe_key: str,
) -> Dict[str, Any]:
    return {
        "status": "duplicate",
        "ticker": str(existing.get("ticker") or payload.get("ticker") or "").strip(),
        "baseline_run_id": str(existing.get("baseline_run_id") or "").strip(),
        "current_path": str(existing.get("current_path") or "").strip(),
        "path_transition": str(existing.get("path_transition") or "").strip(),
        "action": str(existing.get("action") or "").strip(),
        "dedupe": {
            "event_key": dedupe_key,
            "processed_at_utc": str(existing.get("processed_at_utc") or "").strip(),
        },
    }


async def _process_scenario_router_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run the existing announcement workflow; used by direct and queued ingress."""
    dedupe_key = _choose_scenario_router_event_key(payload)
    if dedupe_key:
        existing = _load_scenario_router_dedupe(dedupe_key)
        if existing:
            return _scenario_router_duplicate_response(
                existing=existing,
                payload=payload,
                dedupe_key=dedupe_key,
            )
    from ..scenario_router.inbox_sentinel import InboxSentinel
    from ..scenario_router.lab_scribe import LabScribe

    sentinel = InboxSentinel()
    scribe = LabScribe()
    event = None
    try:
        event = sentinel.ingest_email_payload(payload)
        if not str(event.ticker or "").strip():
            raise HTTPException(
                status_code=400,
                detail="Could not determine ticker from announcement payload.",
            )

        service = _build_scenario_router_service()
        decision = await service.process_announcement_event(event)
    except RuntimeError as exc:
        reason = str(exc or "").strip()
        if event is not None and reason.startswith("No saved lab runs found for "):
            processed_at_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            if dedupe_key:
                _persist_scenario_router_dedupe(
                    dedupe_key,
                    {
                        "event_key": dedupe_key,
                        "processed_at_utc": processed_at_utc,
                        "event_id": event.event_id,
                        "ticker": event.ticker,
                        "baseline_run_id": "",
                        "current_path": "",
                        "path_transition": "",
                        "action": "",
                        "status": "skipped_no_baseline_run",
                        "detail": reason,
                    },
                )
            return {
                "status": "skipped_no_baseline_run",
                "ticker": event.ticker,
                "baseline_run_id": "",
                "current_path": "",
                "path_transition": "",
                "action": "",
                "detail": reason,
            }
        raise HTTPException(
            status_code=500,
            detail=f"Scenario router announcement processing failed: {exc}",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        if event is not None:
            await scribe.persist_status(
                event=event,
                status="processing_error",
                reason=str(exc or "").strip(),
            )
        raise HTTPException(
            status_code=500,
            detail=f"Scenario router announcement processing failed: {exc}",
        ) from exc

    processed_at_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if dedupe_key:
        _persist_scenario_router_dedupe(
            dedupe_key,
            {
                "event_key": dedupe_key,
                "processed_at_utc": processed_at_utc,
                "event_id": decision.event.event_id,
                "ticker": decision.event.ticker,
                "baseline_run_id": decision.baseline_run.run_id,
                "current_path": decision.comparison_report.current_path,
                "path_transition": decision.comparison_report.path_transition,
                "action": decision.action_decision.action,
                "status": "ok",
            },
        )

    return {
        "status": "ok",
        "ticker": decision.event.ticker,
        "baseline_run_id": decision.baseline_run.run_id,
        "current_path": decision.comparison_report.current_path,
        "path_transition": decision.comparison_report.path_transition,
        "action": decision.action_decision.action,
        "dedupe": {
            "event_key": dedupe_key,
            "processed_at_utc": processed_at_utc,
        },
        "decision": decision.to_dict(),
    }


async def start_scenario_router_event_worker() -> None:
    """Recover durable announcement work before accepting new mailbox events."""
    await SCENARIO_ROUTER_EVENT_QUEUE.start(_process_scenario_router_payload)


async def stop_scenario_router_event_worker() -> None:
    await SCENARIO_ROUTER_EVENT_QUEUE.stop()


@router.post("/api/announcement-router/enqueue-announcement", status_code=202)
@router.post("/api/scenario-router/enqueue-announcement", status_code=202)
async def enqueue_scenario_router_announcement(
    request: ProcessScenarioRouterAnnouncementRequest,
    raw_request: Request,
):
    """Durably accept an inbound announcement without waiting for analysis."""
    _check_scenario_router_webhook_secret(raw_request)
    payload = request.model_dump()
    event_key = _choose_scenario_router_event_key(payload)
    if not event_key:
        raise HTTPException(status_code=400, detail="Announcement requires gmail_message_id, event_id, or message_id.")

    existing_dedupe = _load_scenario_router_dedupe(event_key)
    if existing_dedupe:
        return _scenario_router_duplicate_response(
            existing=existing_dedupe,
            payload=payload,
            dedupe_key=event_key,
        )

    queued = await SCENARIO_ROUTER_EVENT_QUEUE.enqueue(event_key, payload)
    record = dict(queued.get("record") or {})
    queue_status = str(record.get("status") or "queued").strip() or "queued"
    if queue_status == "succeeded":
        result = record.get("result") if isinstance(record.get("result"), dict) else {}
        return {
            "status": "duplicate",
            "ticker": str(result.get("ticker") or payload.get("ticker") or "").strip(),
            "queue_status": "succeeded",
            "event_key": event_key,
        }

    return {
        "status": "accepted",
        "event_key": event_key,
        "queue_status": queue_status,
        "attempts": int(record.get("attempts") or 0),
        "created": bool(queued.get("created")),
    }


@router.get("/api/announcement-router/queue")
@router.get("/api/scenario-router/queue")
async def list_scenario_router_queue(limit: int = 50):
    return {"events": SCENARIO_ROUTER_EVENT_QUEUE.list_recent(limit=max(1, min(int(limit or 50), 500)))}
