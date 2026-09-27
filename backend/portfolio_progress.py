"""Execution visibility, kept outside model prompts and request-cache identities."""

from collections import Counter
from datetime import datetime, timezone
import re

from .portfolio_roles import ALLOCATOR_ROLES


PHASES = {
    "research_plan": ("Identifying material research questions", "plans"),
    "research": ("Gathering macro and market research", "requests"),
    "source_text": ("Retrieving cited source text", "batches"),
    "extraction": ("Extracting source-linked facts", "batches"),
    "briefs": ("Building research briefs", "briefs"),
    "source_review": ("Checking facts against sources", "batches"),
    "reconciliation": ("Reconciling the evidence", "reviews"),
    "macro_prior": ("Forming the independent macro allocation", "proposals"),
    "allocators": ("Developing portfolio proposals", "proposals"),
    "comparison": ("Comparing allocation proposals", "reviews"),
    "synthesis": ("Resolving the final allocation", "decisions"),
    "details": ("Developing the selected investment case", "batches"),
    "commentary": ("Writing the memo", "memos"),
    "analysis": ("Analysing the portfolio", "requests"),
}
LANES = {"macro_regime": "Macro outlook", "sector_leadership": "Sector leadership",
         "coverage_audit": "Structural changes and opportunities", "trade_followup": "Trade follow-up"}


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def request_phase(prompt, lane):
    if str(prompt.get("research_contract") or "").startswith("question-led-research-v"):
        return "research_plan"
    if prompt.get("extraction_contract"):
        return "extraction"
    independent_phases = {"blind_macro_prior": "macro_prior", "portfolio_aware_allocator": "allocators",
        "exposure_equivalence_reviewer": "comparison", "defensive_regime_reviewer": "comparison",
        "allocation_comparison": "comparison", "final_allocation": "synthesis", "memo_commentary": "commentary",
        "decision_consistency": "comparison", "settled_decision_consistency": "comparison",
        "decision_reconsideration": "synthesis", "memo_commentary_after_reconsideration": "commentary"}
    base_lane = re.sub(r"(?:_part_\d+)?(?:_source_lookup)?$", "", lane)
    if prompt.get("contract") == "independent-portfolio-v1" and base_lane in independent_phases:
        return independent_phases[base_lane]
    task = str(prompt.get("task", "")).lower()
    for phrase, phase in (("investment details", "details"), ("extract source-linked", "extraction"),
                          ("build source-grounded", "briefs"), ("answer the focused research", "briefs"), ("review source support", "source_review"),
                          ("reconcile portfolio evidence", "reconciliation"),
                          ("explain the recorded", "commentary"), ("portfolio-positioning judge", "comparison"),
                          ("synthesize three", "synthesis"), ("resolve the complementary", "synthesis")):
        if phrase in task:
            return phase
    if prompt.get("lane_strategy") == "blind_macro_prior":
        return "macro_prior"
    if "asset_class_targets" in prompt.get("required_schema", {}):
        return "allocators"
    return "analysis"


def request_label(prompt, lane, phase):
    repairs = {"decision_consistency": "Checking final financial claims", "decision_reconsideration": "Reconsidering affected decisions",
               "settled_decision_consistency": "Checking the revised memo",
               "memo_commentary_after_reconsideration": "Updating commentary for revised decisions"}
    if lane in repairs:
        return repairs[lane]
    batch = re.search(r"(?:batch|investment details)\s+(\d+)", prompt.get("task", ""), re.I)
    if batch:
        prefix = LANES.get(lane, "Source review" if phase == "source_review" else "Investment case")
        return f"{prefix} / batch {batch.group(1)}"
    roles = {role["role"]: role["label"] for role in ALLOCATOR_ROLES}
    section = re.fullmatch(r"(.+)_part_(\d+)(_source_lookup)?", lane)
    if section and section[1] in roles:
        return f"{roles[section[1]]} / section {section[2]}" + (" / source lookup" if section[3] else "")
    return roles.get(prompt.get("lane_strategy")) or roles.get(lane) or LANES.get(lane) or PHASES[phase][0]


def retry_reason(failure):
    return {"output_truncated": "Response reached its output limit",
            "semantic_validation": "Completing missing or invalid fields",
            "in_flight_budget": "Waiting for provider credit reservations to settle",
            "invalid_json": "Repairing the response format"}.get(failure, "Retrying a provider request")


class PortfolioProgress:
    def __init__(self):
        self.tasks = {}
        self.plans = {}
        self.scope = "initial"
        self.status = "running"
        self.started_at = now()
        self.last_result_at = None
        self.last_completed_at = None
        self.checkpoint = {"status": "not_saved", "saved_at": None, "completed_tasks": 0}
        self.revision = 0

    def phase_id(self, phase):
        return f"{self.scope}.{phase}" if self.scope != "initial" else phase

    def plan(self, phase, total, group="all", **counts):
        key = self.phase_id(phase)
        self.plans.setdefault(key, {})[group] = {"total": total, **counts}

    def register(self, key, phase, label, model, provider="OpenRouter"):
        task_id = f"{self.scope}.{key}" if self.scope != "initial" else key
        if task_id not in self.tasks:
            self.tasks[task_id] = {"id": task_id, "cache_key": key, "phase": self.phase_id(phase), "label": label,
                               "model": model, "provider": provider, "status": "queued",
                               "queued_at": now(), "attempt": 1}
        return task_id

    def update(self, key, **fields):
        self.tasks[key].update(fields)

    def result(self, key, finished_at, *, saved=False, **fields):
        self.last_result_at = finished_at
        self.update(key, status="saving" if saved else "retry_queued", finished_at=finished_at, **fields)

    def committed(self, checkpoint, keys):
        self.checkpoint = checkpoint
        keys = set(keys)
        for task in self.tasks.values():
            if task["cache_key"] in keys and task["status"] == "saving":
                task["status"] = task.get("terminal_status", "complete")
                if task["status"] == "complete":
                    self.last_completed_at = max(self.last_completed_at or "", task.get("finished_at") or now())

    def snapshot(self):
        phases = []
        order = list(PHASES)
        phase_ids = set(self.plans) | {task["phase"] for task in self.tasks.values()}
        def sort_key(key):
            phase = key.rsplit(".", 1)[-1]
            scope = key.split(".", 1)[0] if "." in key else "initial"
            if scope in {"independent", "current", "plays", "challenge"}:
                return ({"independent": .2, "current": .4, "plays": .6, "challenge": 1}[scope], order.index(phase))
            # Follow-up occurs between comparison and final synthesis.
            return (1 if key.startswith("followup.") else 2 if phase in {"synthesis", "details", "commentary"} else 0, order.index(phase))
        for key in sorted(phase_ids, key=sort_key):
            phase = key.rsplit(".", 1)[-1]
            scope = key.split(".", 1)[0] if "." in key else "initial"
            tasks = [task for task in self.tasks.values() if task["phase"] == key]
            counts = Counter(task["status"] for task in tasks)
            plan = self.plans.get(key, {})
            total = max(len(tasks), sum(row["total"] for row in plan.values()))
            queued = counts["queued"] + counts["retry_queued"] + max(0, total - len(tasks))
            prefix = {"followup": "Follow-up: ", "independent": "Independent view: ", "current": "Current exposures: ", "plays": "Investment plays: ", "challenge": "Open questions: "}.get(scope, "")
            phases.append({"id": key, "label": prefix + PHASES[phase][0],
                           "unit": PHASES[phase][1], "total": total, "completed": counts["complete"],
                           "reused": sum(bool(task.get("reused")) for task in tasks), "queued": queued,
                           "running": counts["running"], "checking_credit": counts["checking_credit"],
                           "saving": counts["saving"], "failed": counts["failed"],
                           "retrying": sum(task.get("attempt", 1) > 1 and task["status"] not in {"complete", "failed"} for task in tasks),
                           "facts": sum(row.get("facts", 0) for row in plan.values())})
        unfinished = [row for row in phases if row["queued"] or row["running"] or row["saving"] or row["checking_credit"]]
        current = next((row for row in unfinished if row["running"] or row["saving"] or row["checking_credit"]), None)
        current = current or (unfinished[0] if unfinished else phases[-1] if phases else None)
        active = [dict(task) for task in self.tasks.values() if task["status"] in {"running", "checking_credit", "saving"}]
        timestamp = datetime.fromisoformat(now().replace("Z", "+00:00"))
        for task in active:
            def elapsed(stamp):
                try:
                    return max(0, int((timestamp - datetime.fromisoformat(stamp.replace("Z", "+00:00"))).total_seconds()))
                except (AttributeError, ValueError, TypeError):
                    return 0
            task["elapsed_seconds"] = elapsed(task.get("started_at"))
            task["provider_idle_seconds"] = elapsed(task.get("last_event_at") or task.get("started_at"))
            task["content_idle_seconds"] = elapsed(task.get("last_content_at") or task.get("started_at"))
            # Observational alerts only: they never cancel or resubmit a paid call.
            if task["status"] == "running" and task["elapsed_seconds"] >= 600:
                task["duration_warning"] = ("No provider activity for at least three minutes; the request has not been resubmitted."
                    if task["provider_idle_seconds"] >= 180 else
                    "This request has been running for over ten minutes; provider activity is still arriving.")
        queued = [dict(task) for task in self.tasks.values() if task["status"] in {"queued", "retry_queued"}]
        queued.sort(key=lambda task: (task.get("attempt", 1) <= 1, task["queued_at"]))
        message = "Preparing the analysis"
        if current:
            message = f"{current['label']}: {current['completed']}/{current['total']} {current['unit']} saved"
            if current["running"]:
                message += f"; {current['running']} running"
                received = sum(task.get("received_characters", 0) for task in active if task["phase"] == current["id"])
                if received:
                    message += f"; {received:,} characters received"
            if current["checking_credit"]:
                message += f"; {current['checking_credit']} checking credit"
            if current["queued"]:
                message += f"; {current['queued']} queued"
            if current["retrying"]:
                message += f" ({current['retrying']} retries)"
            if current["failed"]:
                message += f"; {current['failed']} unsuccessful"
        if self.status != "running":
            message = {"complete": "Portfolio analysis complete", "awaiting_credit": "Waiting for credit; completed work is saved",
                       "failed": "Analysis stopped; saved research remains available"}.get(self.status, "Analysis interrupted; saved research remains available")
            active, queued = [], []
        elif any(task.get("duration_warning") for task in active):
            message += "; " + next(task["duration_warning"] for task in active if task.get("duration_warning"))
        self.revision += 1
        failures = [dict(task) for task in self.tasks.values() if task["status"] == "failed"]
        return {"schema_version": 1, "revision": self.revision, "status": self.status,
                "started_at": self.started_at, "current_phase": current["id"] if current else None,
                "message": message, "phases": phases, "active_requests": active,
                "queued_requests": queued[:8], "queued_count": len(queued),
                "failed_requests": failures, "research_failures": sum(task["provider"] != "OpenRouter" for task in failures),
                "research_coverage": getattr(self, "research_coverage", None),
                "research_budget": getattr(self, "research_budget", None),
                "work_plan": getattr(self, "work_plan", None),
                "last_result_at": self.last_result_at, "last_completed_at": self.last_completed_at,
                "checkpoint": dict(self.checkpoint)}
