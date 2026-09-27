"""Point-in-time links to saved company research, without score-to-return conversion."""

import json
from pathlib import Path

from .portfolio_evidence import timestamp
from .portfolio_runtime import business_data, digest


def company_announcements(ticker: str, run_id: str, cutoff: str, events_dir: Path) -> tuple[list[dict], list[str]]:
    from .scenario_router.lab_scribe import LabScribe
    paths = set((events_dir / LabScribe._safe_key(ticker)).glob("*.json"))
    if run_id:
        paths.update((events_dir / "by_run" / LabScribe._safe_key(run_id)).glob("*.json"))
    events, issues = {}, []
    for path in sorted(paths):
        try:
            event = json.loads(path.read_text())
            saved = timestamp(event.get("saved_at_utc"))
            if not saved:
                issues.append(f"Announcement date unavailable: {path.name}")
                continue
            if saved > timestamp(cutoff):
                continue
            source = event.get("event") or {}
            if source.get("ticker") and str(source["ticker"]).upper() != ticker.upper():
                continue
            packet = event.get("announcement_packet") or {}
            event_id = str(source.get("event_id") or digest(packet))
            if event_id in events and events[event_id][0] >= saved:
                continue
            status = event.get("status") or "ok"
            events[event_id] = (saved, {"event_id": event_id, "saved_at": saved.isoformat(), "status": status,
                "source": business_data(source), "packet": business_data(packet),
                "facts": business_data(event.get("announcement_facts") or {}),
                "comparison": business_data(event.get("comparison_report") or {}),
                "error": business_data(event.get("error") or {}), "artifact_hash": digest(event)})
        except (ValueError, OSError, TypeError) as exc:
            issues.append(f"Announcement could not be read: {path.name}: {exc}")
    records = [value[1] for value in sorted(events.values(), key=lambda item: item[0])]
    issues.extend(f"Announcement {row['event_id']}: {row['status']}" for row in records if row["status"] not in {"ok", "duplicate"})
    return records, list(dict.fromkeys(issues))


async def attach_company_runs(snapshot: dict, cutoff: str, *, listing=None) -> None:
    from .routers.runs import list_gantt_runs
    listing = listing or list_gantt_runs
    for position in snapshot.get("positions", []):
        ticker = str(position.get("ticker") or "").upper()
        if position.get("council_run_id") or ":" not in ticker:
            continue
        try:
            candidates = (await listing(limit=1000, ticker=ticker)).get("runs") or []
            eligible = [(timestamp(row.get("analysis_date")), row) for row in candidates if str(row.get("ticker") or "").upper() == ticker]
            eligible = [(date, row) for date, row in eligible if date and timestamp(cutoff) and date <= timestamp(cutoff)]
            if eligible:
                position["council_run_id"] = max(eligible, key=lambda item: item[0])[1]["id"]
        except (OSError, ValueError, KeyError) as exc:
            position["company_link_error"] = str(exc)


def link_company_evidence(snapshot: dict, cutoff: str, *, resolver=None, events_dir=None) -> list[dict]:
    from .jobs.runs import _resolve_run_artifact_path
    from .jobs.structured import _extract_stage3_structured_from_artifact
    from .scenario_router.lab_scribe import LabScribe, SCENARIO_ROUTER_EVENTS_DIR

    resolver = resolver or _resolve_run_artifact_path
    events_dir = Path(events_dir or SCENARIO_ROUTER_EVENTS_DIR)
    result = []
    for position in snapshot.get("positions", []):
        run_id = str(position.get("council_run_id") or "")
        record = {"ticker": position.get("ticker"), "asset_class": position.get("asset_class"),
                  "portfolio_pct": position.get("portfolio_pct"), "run_id": run_id, "announcements": []}
        announcements, issues = company_announcements(str(position.get("ticker") or ""), run_id, cutoff, events_dir)
        record.update(announcements=announcements, coverage_issues=issues)
        if not run_id:
            result.append({**record, "status": "not_linked", "reason": position.get("company_link_error") or "No dated company run matched this holding; attach a council run or an exchange-qualified ticker"})
            continue
        try:
            path = resolver(Path(run_id).name)
            payload = json.loads(path.read_text())
            structured = _extract_stage3_structured_from_artifact(payload) or {}
            date = timestamp(payload.get("updated_at") or structured.get("analysis_date") or payload.get("created_at"))
            if not date or not timestamp(cutoff) or date > timestamp(cutoff):
                raise ValueError("Company research date is unknown or later than the portfolio research cutoff")
            company = structured.get("company")
            ticker = str(structured.get("ticker") or (company.get("ticker") if isinstance(company, dict) else "") or "")
            if ticker and ticker.upper() != str(position.get("ticker") or "").upper():
                raise ValueError("Company run ticker does not match the holding")
            record.update(status="linked", research_date=date.isoformat(), artifact_hash=digest(payload),
                          age_days=(timestamp(cutoff) - date).days, company_analysis=business_data(structured))
        except (ValueError, OSError) as exc:
            record.update(status="unavailable", reason=str(exc))
        result.append(record)
    return result
