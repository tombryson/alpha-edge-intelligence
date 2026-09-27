from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from .lab_scribe import SCENARIO_ROUTER_EVENTS_DIR

REVIEWS_DIR = SCENARIO_ROUTER_EVENTS_DIR / "reviews"
VALID_REVIEW_STATUSES = {"open", "reviewed", "dismissed"}
VALID_OVERRIDE_STATES = {
    "no_thesis_change",
    "thesis_strengthened",
    "thesis_weakened",
    "timeline_accelerated",
    "timeline_delayed",
    "risk_reduced",
    "risk_increased",
}
OVERRIDE_DIRECTIONS = {
    "no_thesis_change": "neutral",
    "thesis_strengthened": "positive",
    "timeline_accelerated": "positive",
    "risk_reduced": "positive",
    "thesis_weakened": "negative",
    "timeline_delayed": "negative",
    "risk_increased": "negative",
}
OVERRIDE_LABELS = {
    "no_thesis_change": "No thesis change",
    "thesis_strengthened": "Thesis strengthened",
    "thesis_weakened": "Thesis weakened",
    "timeline_accelerated": "Timeline accelerated",
    "timeline_delayed": "Timeline delayed",
    "risk_reduced": "Risk reduced",
    "risk_increased": "Risk increased",
}


def load_review(event_id: str, *, base_dir: Path = REVIEWS_DIR) -> Dict[str, Any]:
    key = _safe_key(event_id)
    if not key:
        return {}
    path = Path(base_dir) / f"{key}.json"
    if not path.exists() or not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def save_review(
    event_id: str,
    *,
    status: str,
    note: str = "",
    actor: str = "analyst",
    owner: str = "",
    router_override: Dict[str, Any] | None = None,
    base_dir: Path = REVIEWS_DIR,
) -> Dict[str, Any]:
    event_key = _safe_key(event_id)
    status_key = str(status or "").strip().lower()
    if not event_key:
        raise ValueError("event_id is required")
    if status_key not in VALID_REVIEW_STATUSES:
        raise ValueError(f"status must be one of: {', '.join(sorted(VALID_REVIEW_STATUSES))}")

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    existing = load_review(event_key, base_dir=base_dir)
    payload = {
        **existing,
        "event_id": event_key,
        "review_status": status_key,
        "review_note": str(note or "").strip(),
        "reviewed_by": str(actor or "analyst").strip() or "analyst",
        "review_owner": str(owner or actor or "analyst").strip() or "analyst",
        "reviewed_at_utc": now,
        "updated_at_utc": now,
    }
    override = normalize_router_override(router_override)
    if override:
        payload["router_override"] = override
    elif "router_override" in payload and status_key == "dismissed":
        payload.pop("router_override", None)
    if not existing.get("created_at_utc"):
        payload["created_at_utc"] = now

    directory = Path(base_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{event_key}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    return payload


def normalize_router_override(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    state = str(value.get("trajectory_state") or value.get("state") or "").strip().lower()
    if state not in VALID_OVERRIDE_STATES:
        return {}
    direction = OVERRIDE_DIRECTIONS.get(state, "neutral")
    return {
        "trajectory_state": state,
        "trajectory_label": OVERRIDE_LABELS.get(state, state.replace("_", " ").title()),
        "impact_verdict": str(value.get("impact_verdict") or direction).strip().lower() or direction,
        "impact_dimension": str(value.get("impact_dimension") or "manual_review").strip().lower() or "manual_review",
        "filing_type": str(value.get("filing_type") or "company_event").strip().lower() or "company_event",
        "classification_reason": str(value.get("classification_reason") or "Human analyst assigned this router outcome.").strip(),
        "review_note": str(value.get("review_note") or "").strip(),
    }


def apply_review_overlay(row: Dict[str, Any], review: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(row, dict) or not isinstance(review, dict) or not review:
        return row
    status = str(review.get("review_status") or "").strip().lower()
    if status not in VALID_REVIEW_STATUSES or status == "open":
        row["review_overlay"] = review
        return row

    display = row.get("display") if isinstance(row.get("display"), dict) else {}
    override = normalize_router_override(review.get("router_override"))
    label = {
        "reviewed": "Reviewed",
        "dismissed": "Cleared",
    }.get(status, status.title())
    if override:
        row["trajectory_state"] = override["trajectory_state"]
        row["impact_verdict"] = override["impact_verdict"]
        row["impact_dimension"] = override["impact_dimension"]
        row["filing_type"] = override["filing_type"]
        row["classification_reason"] = override["classification_reason"]
    row["display"] = {
        **display,
        **({
            "trajectory_state": override["trajectory_state"],
            "trajectory_label": override["trajectory_label"],
            "impact_verdict": override["impact_verdict"],
            "impact_dimension": override["impact_dimension"],
            "filing_type": override["filing_type"],
            "primary_reason": override["classification_reason"],
        } if override else {}),
        "queue_bucket": str(display.get("queue_bucket") or "").strip(),
        "queue_label": str(display.get("queue_label") or "").strip(),
        "review_status": status,
        "review_label": label,
        "review_owner": str(review.get("review_owner") or "").strip(),
        "is_user_action_required": False,
    }
    row["review_overlay"] = review
    return row


def _safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._:-]+", "_", str(value or "").strip())[:180]
