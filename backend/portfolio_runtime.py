"""Per-run model receipts and checkpointed recovery for portfolio analysis."""

from __future__ import annotations

import asyncio
import contextvars
from copy import deepcopy
import hashlib
import json
import os
import threading
import signal
from contextlib import contextmanager
import re
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .portfolio_progress import PortfolioProgress, request_phase, request_label, retry_reason, LANES
from .portfolio_tokens import OUTPUT_LIMIT_KEYS, without_output_limit

STREAM_FLUSH_SECONDS = 5


@contextmanager
def worker_shutdown(runtime):
    """Stop admission and cancel the owning workflow once; let its writers drain."""
    loop, owner = asyncio.get_running_loop(), asyncio.current_task()
    previous = signal.getsignal(signal.SIGTERM)
    def stop():
        if not runtime.stopping:
            runtime.stopping = True
            owner.cancel()
    loop.add_signal_handler(signal.SIGTERM, stop)
    try:
        yield
    finally:
        loop.remove_signal_handler(signal.SIGTERM)
        signal.signal(signal.SIGTERM, previous)


async def durable_thread(call, *args):
    """Cancellation cannot release the commit lock while its thread still writes."""
    writer = asyncio.create_task(asyncio.to_thread(call, *args))
    cancelled = None
    while True:
        try:
            result = await asyncio.shield(writer)
            break
        except asyncio.CancelledError as exc:
            cancelled = exc
            if writer.cancelled():
                raise
    if cancelled:
        raise cancelled
    return result


async def copy_json_cooperatively(value):
    """Copy assembled JSON without monopolising stream consumption on the loop."""
    if not isinstance(value, (dict, list)):
        return deepcopy(value)
    result = {} if isinstance(value, dict) else []
    pending = [(value, result)]
    count = 0
    while pending:
        source, target = pending.pop()
        items = list(source.items()) if isinstance(source, dict) else list(enumerate(source))
        for key, item in items:
            copied = {} if isinstance(item, dict) else [] if isinstance(item, list) else deepcopy(item)
            if isinstance(target, dict):
                target[key] = copied
            else:
                target.append(copied)
            if isinstance(item, (dict, list)):
                pending.append((item, copied))
        count += 1
        if count % 128 == 0:
            await asyncio.sleep(0)
    return result


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def write_json_atomic(path: Path, payload: dict, *, indent: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    # Stream without a whole-document Unicode/UTF-8 copy; escaped text is lossless.
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=True, indent=indent)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def business_data(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: business_data(item) for key, item in value.items()
                if key not in {"prompt_audit", "judge_prompt_audit", "stage_receipts", "raw_response", "retained_output", "checkpoint", "execution_progress", "checkpoint_info", "payload_accounting"}}
    if isinstance(value, list):
        return [business_data(item) for item in value]
    return value


def load_record(parent: Path, value: dict) -> dict:
    reference = value.get("record_ref") if isinstance(value, dict) else None
    if reference is None:
        return value
    if not isinstance(reference, str) or not re.fullmatch(r"[0-9a-f]{64}", reference):
        raise ValueError("Invalid portfolio record reference")
    payload = json.loads((parent / ".portfolio-records" / (reference + ".json")).read_text())
    if digest(payload) != reference:
        raise ValueError("Portfolio record failed its integrity check")
    return payload


def load_cache_entry(parent: Path, value: dict) -> dict:
    value = load_record(parent, value)
    return {**value, "receipt": load_record(parent, value.get("receipt")),
            "result": load_record(parent, value.get("result"))}


def load_checkpoint(path: Path) -> dict:
    """Replay durable request events newer than the materialized checkpoint."""
    saved = json.loads(path.read_text())
    sequence = saved.get("request_event_sequence", 0)
    directory = path.with_name(path.name + ".events")
    for event_path in sorted(directory.glob("*.json")):
        if not event_path.stem.isdigit() or int(event_path.stem) <= sequence:
            continue
        event = json.loads(event_path.read_text())
        key = event["input_hash"]
        if event.get("cache_entry"):
            saved.setdefault("stage_cache", {})[key] = event["cache_entry"]
        rows = [load_record(path.parent, row) for row in saved.get("stage_receipts", [])]
        saved["stage_receipts"] = [row for row in rows if row.get("input_hash") != key] + [
            load_record(path.parent, row) for row in event["receipts"]]
        if event.get("request_state"):
            saved.setdefault("partial_artifact", {}).setdefault("model_request_state", {})[key] = event["request_state"]
        for field, records in event.get("partial_records", {}).items():
            records = load_record(path.parent, records)
            target = saved.setdefault("partial_artifact", {}).setdefault(field, {})
            if field == "analytical_review_batches":
                for role, sections in records.items():
                    target.setdefault(role, {}).update(sections)
            else:
                target.update(records)
        for field, records in event.get("runtime_records", {}).items():
            saved.setdefault(field, {}).update(load_record(path.parent, records))
        saved["request_event_sequence"] = event["sequence"]
        saved["checkpoint_info"] = {**saved.get("checkpoint_info", {}), "saved_at": event["saved_at"],
                                    "request_event_sequence": event["sequence"]}
    return saved


def workload_summary(receipts: list[dict]) -> dict:
    latest = {row.get("input_hash") or row.get("stage"): row for row in receipts}
    requests = {}
    for row in receipts:
        if row.get("request_settings") and not row.get("reused"):
            key = row.get("request_id") or (row.get("input_hash"), row.get("attempt"), row.get("started_at"))
            requests[key] = row
    costs = [(row.get("usage") or {}).get("cost") for row in requests.values()]
    reported = [value for value in costs if isinstance(value, (int, float)) and not isinstance(value, bool)]
    return {"completed_tasks": sum(row.get("status") == "complete" for row in latest.values()),
            "reused_tasks": sum(bool(row.get("reused")) for row in latest.values()),
            "new_model_requests": len(requests), "retry_requests": sum(row.get("attempt", 1) > 1 for row in requests.values()),
            "reported_openrouter_usd": round(sum(reported), 6), "unpriced_model_requests": len(costs) - len(reported),
            "new_research_requests": sum(not row.get("request_settings") and not row.get("reused")
                and row.get("status") != "blocked" and row.get("failure_type") not in
                {"budget_deferred", "dependency_failed", "funding_unavailable", "provider_outcome_uncertain"}
                for row in latest.values()),
            "deferred_research_tasks": sum(row.get("failure_type") == "budget_deferred" for row in latest.values())}


CURRENT_RUNTIME = contextvars.ContextVar("portfolio_runtime", default=None)
CURRENT_LANE = contextvars.ContextVar("portfolio_lane", default="pipeline")
SUPPLEMENTARY_RESEARCH = contextvars.ContextVar("portfolio_supplementary_research", default=False)

MAX_ATTEMPTS = 3


def unsupported_response_format(response: dict) -> bool:
    if response.get("error_status") not in {400, 422}:
        return False
    # Providers use structured-outputs, structured_outputs and nested JSON errors.
    detail = re.sub(r"[-_]+", " ", str(response.get("error_body") or response.get("error") or "").lower())
    return any(term in detail for term in ("response format", "json object", "json schema", "structured output"))


def receipt_error(receipt: dict) -> str:
    label = str(receipt.get("stage") or "Unknown stage")
    if receipt.get("model"):
        label += f" [{receipt['model']}]"
    if receipt.get("finish_reason") in {"length", "max_tokens"}:
        budget = (receipt.get("request_settings") or {}).get("max_tokens")
        detail = f"Output truncated at {budget:,} tokens" if isinstance(budget, int) else "Output truncated by the model provider"
    else:
        detail = receipt.get("error") or "; ".join(receipt.get("validation_errors") or []) or "Stage incomplete"
    return f"{label}: {detail}"


class PortfolioDependencyError(RuntimeError):
    """A required stage failed; its dependants must not spend more tokens."""


class PortfolioArtifactWriteError(OSError):
    """The recovery checkpoint committed, but its readable artifact did not."""

    def __init__(self, committed):
        super().__init__("Checkpoint saved, but the portfolio artifact could not be updated")
        self.committed = committed


def code_manifest() -> dict:
    root = Path(__file__).resolve().parent.parent
    paths = [root / "portfolio_positioning_memo.py", root / "scripts/portfolio_positioning_memo.py", *sorted((root / "backend").glob("portfolio_*.py")),
             root / "backend/research/providers/perplexity.py", root / "backend/research/providers/tavily.py",
             root / "backend/research/providers/xai.py",
             root / "backend/openrouter.py"]
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


class PortfolioRuntime:
    def __init__(self, checkpoint: Path | None = None, resume: Path | None = None, *, artifact_path: Path | None = None, record_store: bool = False):
        self.checkpoint = checkpoint
        self.artifact_path = artifact_path
        self.partial = {"analysis_kind": "portfolio_positioning", "pipeline_status": "running",
                        "play_assessment_mode": "brief",
                        "structured_data": {"analysis_kind": "portfolio_positioning", "asset_class_targets": []}}
        self.receipts: list[dict] = []
        self.cache: dict[str, dict] = {}
        self.provider_tasks: dict[str, dict] = {}
        self.provider_task_locks: dict[str, asyncio.Lock] = {}
        self.research_reservations: dict[str, dict] = {}
        self.carried_research_estimate_usd = 0.0
        self.provider_funding: dict[str, dict] = {}
        self.started_at = utc_now()
        self.code = code_manifest()
        self.previous_code = None
        self.cache_code_manifests = []
        self.previous_receipts = []
        self.workflow_version = 4
        self.record_store = record_store
        self.funding_guard = None
        self.stopping = False
        self._stored_records = set()
        self._record_memo = {}
        self.model_slots = asyncio.Semaphore(4)
        self._save_lock = asyncio.Lock()
        self._writer_lock = threading.Lock()
        self._snapshot_version = 0
        self._written_version = 0
        self._save_requested = 0
        self._save_committed = 0
        self._request_event_sequence = 0
        self.checkpoint_metrics = {"requests": 0, "coalesced_requests": 0, "writes": 0,
            "record_hashes": 0, "record_reuses": 0,
            "snapshot_seconds": 0.0, "writer_wait_seconds": 0.0, "record_seconds": 0.0,
            "checkpoint_write_seconds": 0.0, "artifact_write_seconds": 0.0,
            "request_events": 0, "request_event_seconds": 0.0, "request_event_bytes": 0}
        self.progress = PortfolioProgress()
        if resume:
            saved = load_checkpoint(resume)
            self._request_event_sequence = saved.get("request_event_sequence", 0)
            self.workflow_version = int(saved.get("workflow_version", 1))
            self.cache = {key: load_cache_entry(resume.parent, value) for key, value in saved.get("stage_cache", {}).items()}
            self.provider_tasks = saved.get("provider_tasks", {})
            self.research_reservations = saved.get("research_reservations", {})
            self.carried_research_estimate_usd = sum(row.get("estimate_usd", 0) for row in self.research_reservations.values()
                                                    if row.get("status") != "rejected")
            # Restore research records, not the aggregate later-phase evidence or old decisions.
            # The runner admits each record at its original information boundary.
            partial = saved.get("partial_artifact") or {}
            # Existing checkpoints retain their research contract; fresh runs use concise plays.
            self.partial["play_assessment_mode"] = partial.get("play_assessment_mode", "components")
            for field in ("targeted_research_results", "research_phase_results", "research_phases", "research_lane_archive", "source_extractions", "document_sections", "document_inspections", "model_request_state", "observation_checks"):
                if field in partial:
                    self.partial[field] = deepcopy(partial[field])
            archive = [*self.partial.get("research_lane_archive", []), *(lane for lane in partial.get("evidence_runs", [])
                if lane.get("supplementary") or str(lane.get("label", "")).startswith(("question_", "trade_followup_")))]
            self.partial["research_lane_archive"] = list({digest(lane): deepcopy(lane) for lane in archive}.values())
            self.started_at = saved.get("research_cutoff", self.started_at)
            self.previous_code = saved.get("code_manifest")
            self.previous_receipts = [load_record(resume.parent, row) for row in saved.get("stage_receipts", [])]
            self.progress.checkpoint = {**saved.get("checkpoint_info", {}), "status": "saved",
                                        "completed_tasks": self._completed_cache_count(), "resumed": True}
            # Version-one checkpoints stored the manifest only in the adjacent artifact.
            artifact = resume.with_name(resume.name.replace(".checkpoint.json", ".json"))
            if not self.previous_code and artifact != resume and artifact.exists():
                self.previous_code = json.loads(artifact.read_text()).get("provenance", {}).get("code_manifest")
            for manifest in [self.previous_code, *(saved.get("cache_code_manifests") or [])]:
                if isinstance(manifest, dict) and manifest not in self.cache_code_manifests:
                    self.cache_code_manifests.append(manifest)

    def require(self, ready: bool, stage: str, reason: str) -> None:
        if ready:
            return
        latest = {row.get("input_hash", row["stage"]): row for row in self.receipts}
        failures = [row for row in latest.values() if row["status"] == "failed"]
        detail = reason
        if failures:
            row = failures[-1]
            detail += f" Cause: {row['stage']} ({row.get('model') or 'research'}): " + (row.get("error") or "; ".join(row.get("validation_errors") or []))
        self.receipts.append({"stage": stage, "input_hash": digest({"blocked": stage}),
                              "status": "blocked", "failure_type": "dependency_failed", "error": detail,
                              "started_at": utc_now(), "finished_at": utc_now()})
        self.save()
        raise PortfolioDependencyError(detail)

    def update_partial(self, **fields) -> None:
        self.partial.update(fields)
        self.save()

    async def aupdate_partial(self, **fields) -> None:
        self.partial.update(fields)
        await self.asave()

    def plan(self, phase, total, group="all", **counts):
        self.progress.plan(phase, total, group, **counts)
        self._report_progress()

    def finish(self, status):
        self.progress.status = status

    def _completed_cache_count(self):
        return len({entry["receipt"].get("input_hash") or key for key, entry in self.cache.items()
                    if isinstance(entry.get("receipt"), dict) and isinstance(entry.get("result"), dict)
                    and entry["receipt"].get("status") == "complete" and not entry["result"].get("error")})

    def _snapshot(self, partial=None) -> tuple:
        started = time.monotonic()
        self._snapshot_version += 1
        # Accepted receipts/cache values are immutable. Partial analysis is still being assembled.
        partial = deepcopy(self.partial) if partial is None else partial
        receipts = list(self.receipts)
        info = {"status": "saved", "saved_at": utc_now(), "sequence": self._snapshot_version,
                "completed_tasks": self._completed_cache_count()}
        saved_progress = deepcopy(self.progress)
        saved_progress.committed(info, self.cache)
        visibility = {"execution_progress": saved_progress.snapshot(), "checkpoint_info": info}
        checkpoint = {"schema_version": 2, "workflow_version": self.workflow_version,
                      "request_event_sequence": self._request_event_sequence,
                      "research_cutoff": self.started_at, "code_manifest": self.code,
                      "cache_code_manifests": list(self.cache_code_manifests), "stage_cache": dict(self.cache),
                      "provider_tasks": deepcopy(self.provider_tasks),
                      "research_reservations": deepcopy(self.research_reservations),
                      "stage_receipts": receipts, "partial_artifact": partial, **visibility}
        artifact = {**partial, "schema_version": 4 if self.workflow_version >= 3 else 3, "workflow_version": self.workflow_version,
                    "id": self.artifact_path.name if self.artifact_path else "",
                    "updated_at": utc_now(), "stage_receipts": receipts,
                    "workload": workload_summary(receipts),
                    "provenance": {**partial.get("provenance", {}), "research_cutoff": self.started_at, "code_manifest": self.code}, **visibility}
        self.checkpoint_metrics["snapshot_seconds"] += time.monotonic() - started
        checkpoint["checkpoint_metrics"] = dict(self.checkpoint_metrics)
        artifact["checkpoint_metrics"] = dict(self.checkpoint_metrics)
        return self._snapshot_version, checkpoint, artifact

    def _write_snapshot(self, version: int, checkpoint: dict, artifact: dict) -> None:
        waiting = time.monotonic()
        with self._writer_lock:
            self.checkpoint_metrics["writer_wait_seconds"] += time.monotonic() - waiting
            if version <= self._written_version:
                return
            started = time.monotonic()
            if self.record_store and self.workflow_version >= 2:
                live_records = {id(row) for row in checkpoint["stage_receipts"]}
                live_records.update(id(value[field]) for value in checkpoint["stage_cache"].values() for field in ("receipt", "result"))
                self._record_memo = {key: value for key, value in self._record_memo.items() if key in live_records}
                checkpoint = {**checkpoint, "schema_version": 3,
                    "stage_cache": {key: {"receipt": self._store_record(value["receipt"]), "result": self._store_record(value["result"])}
                                    for key, value in checkpoint["stage_cache"].items()},
                    "stage_receipts": self._receipt_index(checkpoint["stage_receipts"]),
                    "partial_artifact": business_data(checkpoint["partial_artifact"])}
                artifact = {**business_data(artifact), "stage_receipts": self._receipt_index(artifact["stage_receipts"]),
                            "execution_progress": artifact["execution_progress"], "checkpoint_info": artifact["checkpoint_info"]}
            self.checkpoint_metrics["record_seconds"] += time.monotonic() - started
            checkpoint["checkpoint_metrics"] = dict(self.checkpoint_metrics)
            started = time.monotonic()
            write_json_atomic(self.checkpoint, checkpoint)
            self.checkpoint_metrics["checkpoint_write_seconds"] += time.monotonic() - started
            self.checkpoint_metrics["writes"] += 1
            self._written_version = version
            committed = checkpoint["checkpoint_info"], list(checkpoint["stage_cache"])
            try:
                if self.artifact_path:
                    artifact["checkpoint_metrics"] = dict(self.checkpoint_metrics)
                    started = time.monotonic()
                    write_json_atomic(self.artifact_path, artifact)
                    self.checkpoint_metrics["artifact_write_seconds"] += time.monotonic() - started
            except (OSError, ValueError, TypeError) as exc:
                raise PortfolioArtifactWriteError(committed) from exc
            return committed

    def _store_record(self, value: dict) -> dict:
        cached = self._record_memo.get(id(value))
        # Compare a frozen structure before reusing its digest. Immutable long strings
        # are shared by deepcopy; a nested edit still invalidates the reference.
        if cached and cached[0] is value and cached[1] == value:
            self.checkpoint_metrics["record_reuses"] += 1
            return {"record_ref": cached[2]}
        reference = digest(value)
        self.checkpoint_metrics["record_hashes"] += 1
        if reference not in self._stored_records:
            path = self.checkpoint.parent / ".portfolio-records" / (reference + ".json")
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False) as stream:
                    temporary = Path(stream.name)
                    try:
                        json.dump(value, stream, ensure_ascii=True)
                        stream.flush()
                        os.fsync(stream.fileno())
                        stream.close()
                        temporary.replace(path)
                        directory = os.open(path.parent, os.O_RDONLY)
                        try:
                            os.fsync(directory)
                        finally:
                            os.close(directory)
                    finally:
                        temporary.unlink(missing_ok=True)
            self._stored_records.add(reference)
        self._record_memo[id(value)] = (value, deepcopy(value), reference)
        return {"record_ref": reference}

    def _receipt_index(self, receipts: list) -> list:
        return [{**{key: value for key, value in row.items() if key not in
                    {"prompt", "request_messages", "raw_response", "retained_output"}}, **self._store_record(row)} for row in receipts]

    def persist_artifact(self, artifact: dict) -> None:
        with self._writer_lock:
            artifact = {**artifact, "workflow_version": self.workflow_version,
                        "workload": workload_summary(artifact.get("stage_receipts", []))}
            if self.record_store and self.workflow_version >= 2:
                artifact = {**business_data(artifact), "stage_receipts": self._receipt_index(artifact.get("stage_receipts", []))}
            artifact.update(execution_progress=self.progress.snapshot(), checkpoint_info=dict(self.progress.checkpoint))
            artifact["checkpoint_metrics"] = dict(self.checkpoint_metrics)
            write_json_atomic(self.artifact_path, artifact, indent=2)

    def save(self) -> None:
        if self.checkpoint:
            self._save_requested += 1
            self.checkpoint_metrics["requests"] += 1
            ticket = self._save_requested
            try:
                self._saved(self._write_snapshot(*self._snapshot()))
                self._save_committed = max(ticket, self._save_committed)
            except Exception as exc:
                self._save_failed(exc)
                raise
            self._report_progress()

    async def asave(self) -> None:
        if self.checkpoint:
            self._save_requested += 1
            self.checkpoint_metrics["requests"] += 1
            ticket = self._save_requested
            async with self._save_lock:
                if ticket <= self._save_committed:
                    self.checkpoint_metrics["coalesced_requests"] += 1
                    return
                # One snapshot covers every mutation submitted before it was taken.
                covered = self._save_requested
                try:
                    # Freeze admission guards before yielding. A later result event
                    # advances them; a boundary snapshot must never clear a pending
                    # paid request without committing its response alongside it.
                    fields = dict(self.partial)
                    fields["model_request_state"] = deepcopy(fields.get("model_request_state", {}))
                    started = time.monotonic()
                    partial = await copy_json_cooperatively(fields)
                    self.checkpoint_metrics["snapshot_seconds"] += time.monotonic() - started
                    self._saved(await durable_thread(self._write_snapshot, *self._snapshot(partial)))
                    self._save_committed = max(covered, self._save_committed)
                except Exception as exc:
                    self._save_failed(exc)
                    raise
                self._report_progress()

    async def asave_request(self, key: str, *, partial_records=None, runtime_records=None) -> None:
        # Legacy/test runtimes retain their standalone checkpoint contract.
        if not self.record_store or not self.checkpoint:
            await self.asave()
            return
        if not self.checkpoint.exists():
            await self.asave()
        async with self._save_lock:
            started = time.monotonic()
            sequence = self._request_event_sequence + 1
            event = {"sequence": sequence, "input_hash": key, "saved_at": utc_now(),
                "cache_entry": deepcopy(self.cache.get(key)),
                "receipts": deepcopy([row for row in self.receipts if row.get("input_hash") == key]),
                "partial_records": deepcopy(partial_records or {}),
                "runtime_records": deepcopy(runtime_records or {}),
                "request_state": deepcopy(self.partial.get("model_request_state", {}).get(key))}
            cancelled = None
            writer = asyncio.create_task(asyncio.to_thread(self._write_request_event, event))
            try:
                while True:
                    try:
                        size = await asyncio.shield(writer)
                        break
                    except asyncio.CancelledError as exc:
                        # Keep the sequence lock until the thread settles, including
                        # repeated cancellation, so the next event cannot overwrite it.
                        cancelled = exc
                        if writer.cancelled():
                            self._request_event_sequence = sequence
                            raise
            except Exception as exc:
                self._save_failed(exc)
                raise
            self._request_event_sequence = sequence
            self.checkpoint_metrics["request_events"] += 1
            self.checkpoint_metrics["request_event_seconds"] += time.monotonic() - started
            self.checkpoint_metrics["request_event_bytes"] += size
            self.progress.committed({**self.progress.checkpoint, "status": "saved", "saved_at": event["saved_at"],
                "request_event_sequence": sequence, "completed_tasks": self._completed_cache_count()}, self.cache)
            self._report_progress()
            if cancelled:
                raise cancelled

    def _write_request_event(self, event):
        with self._writer_lock:
            entry = event["cache_entry"]
            event = {**event, "receipts": self._receipt_index(event["receipts"]),
                     "partial_records": {field: self._store_record(rows) for field, rows in event.get("partial_records", {}).items()},
                     "runtime_records": {field: self._store_record(rows) for field, rows in event.get("runtime_records", {}).items()},
                     "cache_entry": {field: self._store_record(entry[field]) for field in ("receipt", "result")} if entry else None}
            path = self.checkpoint.with_name(self.checkpoint.name + ".events") / f"{event['sequence']:012}.json"
            write_json_atomic(path, event)
            return path.stat().st_size

    def _saved(self, result):
        if result:
            self.progress.committed(*result)

    def _save_failed(self, error):
        if isinstance(error, PortfolioArtifactWriteError):
            self._saved(error.committed)
            self.progress.checkpoint = {**self.progress.checkpoint, "artifact_status": "failed"}
        else:
            self.progress.checkpoint = {**self.progress.checkpoint, "status": "failed", "error": "Checkpoint write failed"}
        self._report_progress()

    def _report_progress(self):
        if self.artifact_path:
            print("portfolio progress: " + json.dumps({**workload_summary(self.receipts),
                  "execution_progress": self.progress.snapshot()}), flush=True)

    async def research(self, name: str, inputs: dict, call: Callable, *, required: bool = True) -> dict:
        if self.stopping:
            raise asyncio.CancelledError()
        # Retrieval is frozen data, independent of subsequent analysis-code changes.
        key = self.research_key(name, inputs)
        phase = "source_text" if "citation" in name else "research"
        provider = {"grok_research": "xAI", "perplexity": "Perplexity", "tavily": "Tavily", "parallel": "Parallel"}.get(name, "Parallel" if inputs.get("provider") == "parallel" else "Source retrieval")
        label = inputs.get("question") or LANES.get(CURRENT_LANE.get(), "Sources")
        progress_key = self.progress.register(key, phase, f"{label} / {provider}", inputs.get("model"), provider)
        if key not in self.cache:
            for code in self.cache_code_manifests:
                legacy_key = digest({"stage": name, "inputs": inputs, "cutoff": self.started_at, "code": code})
                if legacy_key in self.cache:
                    self.cache[key] = self.cache[legacy_key]
                    break
        if key in self.cache:
            cached = self.cache[key]
            self.receipts.append({**cached["receipt"], "reused": True, "optional": not required or SUPPLEMENTARY_RESEARCH.get()})
            self.partial.setdefault("retained_research", {})[key] = {"stage": name, "result": cached["result"]}
            self.progress.update(progress_key, status="failed" if cached["result"].get("error") else "complete", reused=True)
            self._report_progress()
            # Already durable in the parent checkpoint; persist at the next boundary or new result.
            return deepcopy(cached["result"])
        started = utc_now()
        self.progress.update(progress_key, status="running", started_at=started)
        self._report_progress()
        try:
            result = await call()
        except Exception as exc:
            result = {"error": f"{type(exc).__name__}: {str(exc) or 'Research request failed'}", "error_type": type(exc).__name__, "results": []}
        if not isinstance(result, dict):
            result = {"error": "Research provider returned no object", "results": []}
        success = result.get("success") is not False and not result.get("error") and bool(result.get("results") or result.get("summary") or result.get("research_summary"))
        if not success:
            result["error_type"] = result.get("error_type") or "empty_research"
            result["error"] = str(result.get("error") or "").strip() or f"{result['error_type']}: research did not return a usable response"
        receipt = {"stage": f"{CURRENT_LANE.get()}:{name}", "model": inputs.get("model") or result.get("model") or (result.get("provider_metadata") or {}).get("model"),
                   "input_hash": key, "started_at": started, "finished_at": utc_now(),
                   "status": "complete" if success else "failed", "error": result.get("error") or "",
                   "failure_type": result.get("error_type", "") if not success else "",
                   "http_status": result.get("http_status"), "request_id": result.get("request_id"),
                   "request_count": result.get("request_count"), "finish_reason": result.get("finish_reason"),
                   "usage": result.get("usage"),
                   "attempts": [{k: v for k, v in attempt.items() if k not in {"raw_response", "partial_text"}}
                                for attempt in result.get("attempts", [])],
                   "provider_metadata": result.get("provider_metadata", {}), "reused": False}
        receipt["optional"] = not required or SUPPLEMENTARY_RESEARCH.get()
        if not required and (not success or result.get("failed_results")):
            receipt.update(completion_mode="with_limitations",
                warnings=[{"detail": "Some source research could not be retrieved. Unsupported claims remain unverified; other research is retained."}])
        receipt["retrieval_status"] = "succeeded" if success else "failed"
        self.receipts.append(receipt)
        self.partial.setdefault("retained_research", {})[key] = {"stage": name, "result": result}
        if success or (not required and not result.get("resumable")):
            self.cache[key] = {"result": result, "receipt": receipt}
        self.progress.result(progress_key, receipt["finished_at"], saved=key in self.cache,
                             terminal_status="complete" if success else "failed", error=result.get("error"), http_status=result.get("http_status"))
        if key not in self.cache:
            self.progress.update(progress_key, status="complete" if success else "failed")
        self._report_progress()
        await self.asave_request(key, partial_records={"retained_research": {key: self.partial["retained_research"][key]}})
        return result

    def research_key(self, name: str, inputs: dict) -> str:
        return digest({"stage": name, "inputs": inputs, "cutoff": self.started_at, "research_contract": 1})

    def has_research(self, name: str, inputs: dict) -> bool:
        keys = [self.research_key(name, inputs), *(digest({"stage": name, "inputs": inputs,
            "cutoff": self.started_at, "code": code}) for code in self.cache_code_manifests)]
        return any(key in self.cache and not self.cache[key]["result"].get("error") for key in keys)

    async def save_provider_task(self, key: str, state: dict) -> None:
        changed = self.provider_tasks.get(key) != state
        self.provider_tasks[key] = deepcopy(state)
        for task in self.progress.tasks.values():
            if task["cache_key"] == key:
                task.update(provider_run_id=state.get("run_id"), provider_status=state.get("status"))
        if changed:
            await self.asave_request("provider:" + key, runtime_records={"provider_tasks": {key: state},
                "research_reservations": self.research_reservations})
        self._report_progress()

    async def query(self, client: Callable, model: str, messages: list, *, parser: Callable, validator: Callable, **kwargs) -> dict:
        if self.stopping:
            raise asyncio.CancelledError()
        from .portfolio_recovery import merge_reviews, review_repair_prompt, recover_reviews, recover_optional_fields, field_repair_prompt, completed_json_fields, retain_terminal_review

        prompt = json.loads(messages[0]["content"])
        prompt = business_data(prompt)
        messages = [{"role": "user", "content": json.dumps(prompt, ensure_ascii=False)}]
        kwargs = without_output_limit(kwargs)
        stage = f"{CURRENT_LANE.get()}:{prompt.get('task', 'structured_output')}"
        contract = {"stage": stage, "model": model, "prompt": prompt, "settings": kwargs, "contract": 3}
        key = digest({**contract, "code": self.code})
        phase = request_phase(prompt, CURRENT_LANE.get())
        progress_key = self.progress.register(key, phase, request_label(prompt, CURRENT_LANE.get(), phase), model)
        self._report_progress()
        previous_key = digest({**contract, "code": self.previous_code}) if self.previous_code else key
        candidate_keys = list(dict.fromkeys([key, previous_key,
            *(digest({**contract, "code": code}) for code in self.cache_code_manifests)]))
        unchanged_settings_keys = set(candidate_keys)
        # A removed output cap must not invalidate an otherwise identical paid answer.
        # Reconstruct old hashes, retaining every other input, setting and code identity.
        legacy_limits = dict.fromkeys(json.dumps({name: value for name, value in (row.get("request_settings") or {}).items()
            if name in OUTPUT_LIMIT_KEYS}, sort_keys=True)
            for row in [*self.previous_receipts, *(entry.get("receipt") or {} for entry in self.cache.values())]
            if row.get("stage") == stage and row.get("model") == model)
        for limits in legacy_limits:
            if limits == "{}":
                continue
            legacy_contract = {**contract, "settings": {**kwargs, **json.loads(limits)}}
            for code in [self.code, self.previous_code, *self.cache_code_manifests]:
                if code:
                    candidate_keys.append(digest({**legacy_contract, "code": code}))
        candidate_keys = list(dict.fromkeys(candidate_keys))
        for candidate_key in candidate_keys:
            cached = self.cache.get(candidate_key)
            if not cached:
                # Recover accepted outputs from older checkpoints or an interrupted cache commit.
                previous = next((row for row in reversed(self.previous_receipts)
                    if row.get("input_hash") == candidate_key and row.get("status") == "complete"), None)
                if previous:
                    result = deepcopy(previous.get("raw_response") or {})
                    if isinstance(previous.get("retained_output"), dict):
                        result["content"] = json.dumps(previous["retained_output"], ensure_ascii=False)
                        result.update(error="", error_type="")
                    result.update(stage_status="complete", warnings=deepcopy(previous.get("warnings") or []))
                    cached = {"receipt": previous, "result": result}
            if not cached:
                continue
            try:
                parsed = parser(cached["result"].get("content") or "")
                valid = (isinstance(parsed, dict) and not validator(parsed, prompt)
                         and isinstance(cached["receipt"], dict)
                         and cached["receipt"].get("status") == "complete"
                         and (candidate_key in unchanged_settings_keys
                              or cached["receipt"].get("finish_reason") not in {"length", "max_tokens"}))
            except (ValueError, TypeError, KeyError, AttributeError):
                valid = False
            if not valid:
                continue
            # Explicit resume may reuse an identical model request after current validation.
            receipt = {**cached["receipt"], "input_hash": key, "reused": True,
                       "optional": SUPPLEMENTARY_RESEARCH.get(),
                       "revalidated": candidate_key != key, "reused_from_input_hash": candidate_key}
            self.receipts.append(receipt)
            self.cache[key] = {"result": deepcopy(cached["result"]), "receipt": receipt}
            if candidate_key != key:
                self.cache.pop(candidate_key, None)
            self.progress.update(progress_key, status="complete", reused=True)
            self._report_progress()
            return deepcopy(cached["result"])
        attempts = []
        request_messages = messages
        review_stage = "fact_checks" in (prompt.get("required_schema") or {})
        retained_reviews, best_parsed = None, None
        repair_base, repair_fields, active_repair = None, set(), None
        if review_stage:
            for previous in self.previous_receipts:
                if previous.get("input_hash") not in candidate_keys or previous.get("finish_reason") in {"length", "max_tokens"}:
                    continue
                candidate = previous.get("retained_output") or parser((previous.get("raw_response") or {}).get("content") or "")
                if isinstance(candidate, dict):
                    retained_reviews = merge_reviews(retained_reviews, candidate, prompt)
            if retained_reviews is not None:
                request_messages = [{"role": "user", "content": json.dumps(review_repair_prompt(prompt, retained_reviews))}]
        options = {**kwargs, "include_error_details": True, "response_format": {"type": "json_object"}}
        # Serving preference is not a new analytical request. Keep completed answers
        # and in-flight identity reusable when only this routing setting changes.
        preference = os.getenv("PORTFOLIO_PROVIDER_SORT", "").strip()
        if preference in {"throughput", "latency", "price"} and getattr(client, "supports_provider_preferences", False):
            options.setdefault("provider_preferences", {"sort": preference, "allow_fallbacks": True})
        attempt_limit = 1 if retained_reviews is not None else MAX_ATTEMPTS

        async def accept(parsed, response, receipt, warnings):
            receipt.update(status="complete", failure_type="", error="", validation_errors=[], warnings=warnings,
                           completion_mode="with_limitations" if warnings else "complete", retained_output=deepcopy(parsed))
            result = {**response, "content": json.dumps(parsed, ensure_ascii=False), "stage_status": "complete",
                      "error": "", "error_type": "", "warnings": warnings}
            # Completion and verification are separate: warnings stay attached on resume.
            self.cache[key] = {"result": deepcopy(result), "receipt": deepcopy(receipt)}
            self.progress.result(progress_key, receipt["finished_at"], saved=True)
            self._report_progress()
            await self.asave_request(key)
            return result

        async def retain_review(receipt, *, reused=False):
            response = receipt.get("raw_response") or {}
            retained, warnings = retain_terminal_review(response, prompt, validator)
            if retained is None:
                return None
            recovery = {**deepcopy(receipt), "input_hash": key, "finished_at": utc_now(),
                "recovery_error": receipt.get("error"), "recovery_kind": "retained_terminal_review",
                "reused": reused, "reused_from_input_hash": receipt.get("input_hash") if reused else None}
            self.receipts.append(recovery)
            if reused:
                self.progress.update(progress_key, reused=True)
            return await accept(retained, {}, recovery, warnings)

        # Known-ended saved requests can be read locally. Never resubmit uncertain work.
        for previous in reversed(self.previous_receipts):
            if previous.get("input_hash") in candidate_keys and previous.get("status") == "failed":
                retained = await retain_review(previous, reused=True)
                if retained is not None:
                    return retained

        for attempt in range(attempt_limit):
            queued = utc_now()
            started = None
            provider_finished = None
            request_checkpoint_seconds = 0.0
            streaming = getattr(client, "supports_progress", False) is True
            stream_events, received_chars, last_flush = [], 0, time.monotonic()
            flush_lock = asyncio.Lock()
            heartbeat_stop = asyncio.Event()
            from .portfolio_requests import payload_accounting
            dispatch_payload = payload_accounting(json.loads(request_messages[0]["content"]))
            dispatch_payload["message_bytes"] = len(json.dumps(request_messages, ensure_ascii=False).encode())
            journal = (self.checkpoint.parent / ".portfolio-streams" / f"{key}.{len(self.receipts)}.{attempt + 1}.jsonl") if self.checkpoint else None
            request_states = self.partial.setdefault("model_request_state", {})
            if streaming:
                pending = next((request_states[candidate] for candidate in candidate_keys
                    if request_states.get(candidate, {}).get("status") in {"submitting", "receiving", "uncertain"}), None)
                if pending:
                    self.progress.update(progress_key, status="failed", activity="provider_outcome_uncertain")
                    await self.asave()
                    return {"content": "", "stage_status": "failed", "error_type": "provider_outcome_uncertain",
                        "error": "A prior paid request has no confirmed outcome. Its stream is saved; verify the provider request before resubmitting.",
                        "provider_request": deepcopy(pending)}

            async def flush_stream():
                nonlocal last_flush
                async with flush_lock:
                    batch = stream_events[:]
                    if batch and journal:
                        def append():
                            journal.parent.mkdir(parents=True, exist_ok=True)
                            with journal.open("a", encoding="utf-8") as output:
                                for event in batch:
                                    output.write(json.dumps(event, ensure_ascii=False) + "\n")
                                output.flush()
                                os.fsync(output.fileno())
                        await asyncio.to_thread(append)
                    # Events received during disk I/O belong to the next flush.
                    del stream_events[:len(batch)]
                    last_flush = time.monotonic()

            async def journal_heartbeat():
                while not heartbeat_stop.is_set():
                    try:
                        await asyncio.wait_for(heartbeat_stop.wait(), timeout=STREAM_FLUSH_SECONDS)
                    except asyncio.TimeoutError:
                        await flush_stream()
                        self._report_progress()

            async def stream_progress(event):
                nonlocal received_chars
                stamp = utc_now()
                stream_events.append({"at": stamp, **event})
                content = event.get("content_delta") or ""
                received_chars += len(content)
                task = self.progress.tasks[progress_key]
                first_event = not request_states[key].get("last_event_at")
                first_identifier = bool(event.get("id")) and not request_states[key].get("provider_request_id")
                fields = {"activity": event.get("activity"), "last_event_at": stamp, "received_characters": received_chars}
                if content:
                    fields.update(last_content_at=stamp, first_content_at=task.get("first_content_at") or stamp)
                if content or event.get("reasoning_delta"):
                    fields["first_token_at"] = task.get("first_token_at") or stamp
                if event.get("id"):
                    fields["provider_request_id"] = event["id"]
                self.progress.update(progress_key, **fields)
                request_states[key].update(status="receiving", provider_request_id=event.get("id") or request_states[key].get("provider_request_id"),
                                          received_characters=received_chars, last_event_at=stamp)
                if time.monotonic() - last_flush >= STREAM_FLUSH_SECONDS or first_event or first_identifier:
                    self._report_progress()
                    await flush_stream()
                # The identifier is fsynced in the journal. Do not stall token consumption
                # behind a full checkpoint rewrite; the submitting checkpoint already guards retries.
            self.progress.update(progress_key, status="retry_queued" if attempt else "queued", queued_at=queued,
                                 started_at=None, attempt=attempt + 1, first_token_at=None, first_content_at=None,
                                 last_content_at=None, last_event_at=None, provider_request_id=None, received_characters=0)
            self._report_progress()
            async def dispatch(*args, **settings):
                nonlocal started, provider_finished, request_checkpoint_seconds
                self.progress.update(progress_key, status="running", activity="saving_request" if streaming else "awaiting_provider",
                    input_characters=sum(len(row.get("content", "")) for row in request_messages))
                self._report_progress()
                if streaming:
                    request_states[key] = {"status": "submitting", "model": model, "prepared_at": utc_now(),
                        "journal": str(journal) if journal else None, "attempt": attempt + 1}
                    checkpoint_started = time.monotonic()
                    await self.asave_request(key)
                    request_checkpoint_seconds = time.monotonic() - checkpoint_started
                    settings["on_progress"] = stream_progress
                started = utc_now()
                if streaming:
                    request_states[key]["started_at"] = started
                self.progress.update(progress_key, status="running", started_at=started, activity="awaiting_provider")
                self._report_progress()
                heartbeat = asyncio.create_task(journal_heartbeat())
                try:
                    return await client(*args, **settings)
                finally:
                    provider_finished = utc_now()
                    heartbeat_stop.set()
                    await heartbeat
                    await flush_stream()
            try:
                async with self.model_slots:
                    if self.stopping:
                        raise asyncio.CancelledError()
                    self.progress.update(progress_key, status="checking_credit")
                    self._report_progress()
                    response = await (self.funding_guard.call(dispatch, model, request_messages,
                        receipts=[*self.previous_receipts, *self.receipts], stage=stage, **options)
                        if self.funding_guard else dispatch(model, request_messages, **options))
            except Exception as exc:
                from .portfolio_funding import FundingRequired
                if isinstance(exc, FundingRequired):
                    optional = SUPPLEMENTARY_RESEARCH.get()
                    if not optional:
                        self.partial["funding"] = exc.report
                    if exc.response is not None:
                        if streaming and key in request_states:
                            request_states[key].update(status="rejected", finished_at=utc_now(),
                                error_status=exc.response.get("error_status"))
                            await flush_stream()
                        from .portfolio_funding import work_kind
                        self.receipts.append({"stage": stage, "model": model, "input_hash": key,
                            "started_at": started, "finished_at": utc_now(), "attempt": attempt + 1,
                            "status": "failed", "failure_type": "credit_rejected", "error_status": 402,
                            "optional": optional,
                            "error": exc.response.get("error"), "raw_response": deepcopy(exc.response),
                            "request_messages": request_messages, "prompt": prompt, "request_settings": options,
                            "work_kind": work_kind(stage, prompt), "reused": False})
                        self.receipts[-1]["payload_accounting"] = dispatch_payload
                    else:
                        self.receipts.append({"stage": stage, "model": model, "input_hash": key,
                            "status": "blocked", "failure_type": "funding_unavailable", "optional": optional,
                            "started_at": None, "finished_at": utc_now(), "error": exc.report["message"],
                            "funding": exc.report, "reused": False})
                    self.progress.update(progress_key, status="failed" if optional else "awaiting_credit")
                    await self.asave()
                    if optional:
                        return {"content": "", "stage_status": "failed", "error_type": "funding_unavailable",
                            "error": exc.report["message"], "warnings": [{"detail":
                                "This supplementary check was not completed. Retained analysis remains available; its conclusions have not been verified by this check."}]}
                    raise
                response = {"content": "", "error": str(exc), "error_type": type(exc).__name__, "error_retryable": False,
                            "outcome_uncertain": streaming and started is not None}
            response = response if isinstance(response, dict) else {"content": "", "error_type": "empty_response"}
            if streaming and key in request_states:
                request_states[key].update(status="uncertain" if response.get("outcome_uncertain") else "finished",
                                          finished_at=utc_now())
                await flush_stream()
            self.progress.update(progress_key, activity="validating_response")
            self._report_progress()
            warnings = []
            try:
                parsed = parser(response.get("content") or "")
                if isinstance(parsed, dict) and repair_base is not None:
                    if (active_repair or {}).get("repair_contract") == "portfolio-path-repair-v1":
                        from .portfolio_recovery import apply_row_repairs
                        parsed = apply_row_repairs(repair_base, parsed, active_repair)
                    else:
                        parsed = {**repair_base, **{key: value for key, value in parsed.items() if key in repair_fields}}
                if isinstance(parsed, dict):
                    best_parsed = deepcopy(parsed)
                if not response.get("error") and not response.get("error_type") and response.get("finish_reason") not in {"length", "max_tokens"}:
                    if review_stage and isinstance(parsed, dict):
                        retained_reviews = merge_reviews(retained_reviews, parsed, prompt)
                        parsed = retained_reviews
                    elif not review_stage:
                        parsed, warnings = recover_optional_fields(parsed, prompt)
                errors = validator(parsed, prompt) if isinstance(parsed, dict) else ["Response was not a JSON object"]
            except (ValueError, TypeError, KeyError, AttributeError) as exc:
                parsed, errors = None, [f"Malformed structured response: {exc}"]
            provider_error = response.get("error") or response.get("error_type")
            if provider_error and response.get("error_body"):
                try:
                    body = json.loads(response["error_body"])
                    detail = body.get("error", body) if isinstance(body, dict) else {}
                    detail = detail.get("message") if isinstance(detail, dict) else detail
                    if detail and str(detail) not in str(provider_error):
                        provider_error = f"{provider_error}: {str(detail)[:500]}"
                except (ValueError, TypeError):
                    pass
            truncated = response.get("finish_reason") in {"length", "max_tokens"}
            if truncated:
                errors = ["Output truncated by the model provider; no application output-token limit was sent. A complete JSON response was not received"]
            failure_type = (str(response.get("error_type") or "provider_error") if provider_error else
                            "output_truncated" if truncated else "semantic_validation" if parsed is not None else "invalid_json")
            error = str(provider_error) if provider_error else "; ".join(errors)
            from .portfolio_funding import work_kind
            receipt = {"stage": stage, "model": model, "input_hash": key, "started_at": started, "queued_at": queued,
                       "work_kind": work_kind(stage, prompt),
                       "payload_accounting": dispatch_payload,
                       "requested_model": model, "resolved_model": response.get("resolved_model") or response.get("model"),
                       "optional": SUPPLEMENTARY_RESEARCH.get(),
                       "request_messages": request_messages,
                       "prompt": prompt, "request_settings": {key: val for key, val in options.items() if key != "include_error_details"},
                       "finished_at": utc_now(), "attempt": attempt + 1, "status": "failed" if provider_error or errors else "complete",
                       "failure_type": failure_type if provider_error or errors else "",
                       "validation_errors": errors, "request_id": response.get("id"), "usage": response.get("usage"),
                       "finish_reason": response.get("finish_reason"), "provider": response.get("provider"),
                       "transport": "stream" if streaming else "nonstreaming", "stream_journal": str(journal) if streaming and journal else None,
                       "error_status": response.get("error_status"), "error": error,
                       "funding_estimate": response.get("funding_estimate"),
                       "raw_response": response, "reused": False}
            if review_stage and attempt_limit == 1:
                receipt["reused_partial_from_input_hash"] = previous_key
            attempts.append(receipt)
            task_timing = self.progress.tasks[progress_key]
            def elapsed(start, end):
                if not start or not end:
                    return None
                return max(0, (datetime.fromisoformat(end.replace("Z", "+00:00")) -
                               datetime.fromisoformat(start.replace("Z", "+00:00"))).total_seconds())
            generation_seconds = elapsed(task_timing.get("first_token_at"), provider_finished)
            output_tokens = (response.get("usage") or {}).get("completion_tokens")
            receipt["timing"] = {"queue_seconds": elapsed(queued, started),
                "request_checkpoint_seconds": request_checkpoint_seconds,
                "time_to_first_token_seconds": elapsed(started, task_timing.get("first_token_at")),
                "time_to_first_content_seconds": elapsed(started, task_timing.get("first_content_at")),
                "generation_seconds": generation_seconds,
                "provider_seconds": elapsed(started, provider_finished),
                "local_completion_seconds": elapsed(provider_finished, receipt["finished_at"]),
                "output_tokens_per_second": output_tokens / generation_seconds if isinstance(output_tokens, (int, float)) and generation_seconds else None,
                "elapsed_seconds": elapsed(started, receipt["finished_at"])}
            self.receipts.append(receipt)
            if receipt["status"] == "complete":
                return await accept(parsed, response, receipt, warnings)
            retained = await retain_review(receipt)
            if retained is not None:
                return retained
            if truncated and not provider_error and (prompt.get("contract") == "independent-portfolio-v1"
                    or "allocation_details" in (prompt.get("required_schema") or {})):
                retained = parsed if isinstance(parsed, dict) else completed_json_fields(response.get("content"))
                schema = prompt.get("required_schema") or {}
                # A delta must arrive in full; otherwise absence could hide an intended change.
                if not prompt.get("update_contract") or isinstance(parsed, dict) and set(schema) <= set(parsed):
                    recovered, recovery_warnings = recover_optional_fields(retained, prompt)
                    if isinstance(recovered, dict) and not validator(recovered, prompt):
                        receipt["provider_truncation_retained"] = True
                        return await accept(recovered, response, receipt, [*recovery_warnings,
                            {"detail": "The provider reached its native output limit. Fully received, validated analysis was retained; missing supplementary fields remain unassessed."}])
            self.progress.result(progress_key, receipt["finished_at"], retry_reason=retry_reason(failure_type))
            await self.asave_request(key)
            if attempt == attempt_limit - 1:
                break
            if provider_error:
                unsupported = "response_format" in options and unsupported_response_format(response)
                if unsupported:
                    options.pop("response_format", None)
                elif response.get("error_retryable"):
                    await asyncio.sleep(0.2)
                else:
                    break
            elif truncated:
                options["reasoning_effort"] = "low"
                # A truncated document is not a repairable answer. Do not resend its bulk.
                request_messages = messages + [{"role": "user", "content":
                    "The previous response reached its output limit. Generate the complete JSON object afresh. "
                    "Be concise within each field, preserve every required item, and do not repeat the source packet or schema."}]
            else:
                if review_stage and retained_reviews is not None:
                    request_messages = [{"role": "user", "content": json.dumps(review_repair_prompt(prompt, retained_reviews))}]
                else:
                    repair = field_repair_prompt(prompt, parsed or repair_base, errors)
                    if repair:
                        repair_base = deepcopy(parsed or repair_base)
                        active_repair = repair
                        repair_fields = set(repair["required_schema"])
                        request_messages = [{"role": "user", "content": json.dumps(repair)}]
                    else:
                        repair_base, repair_fields = None, set()
                        request_messages = messages + [{"role": "user", "content":
                            "The previous response could not be validated. Return the required JSON using the saved evidence; do not repeat the schema or source packet. Validation errors: " + json.dumps(errors)}]
        if review_stage:
            recovered, warnings = recover_reviews(retained_reviews, prompt)
        else:
            recovered, warnings = recover_optional_fields(best_parsed, prompt, exhausted=True)
        can_recover = review_stage or "allocation_details" in (prompt.get("required_schema") or {})
        if can_recover and isinstance(recovered, dict) and not validator(recovered, prompt):
            warning = {"detail": f"Model response incomplete: {attempts[-1]['error']}. Usable output retained; missing details remain unknown."}
            receipt = {**deepcopy(attempts[-1]), "finished_at": utc_now(), "recovery_error": attempts[-1]["error"],
                       "recovered_from_attempts": len(attempts)}
            self.receipts.append(receipt)
            return await accept(recovered, {}, receipt, warnings or [warning])
        self.progress.update(progress_key, status="failed")
        await self.asave_request(key)
        return {"content": "", "stage_status": "failed", "error_type": attempts[-1]["failure_type"],
                "partial_content": json.dumps(best_parsed) if best_parsed is not None else "",
                "partial_proposal": best_parsed if "asset_class_targets" in (prompt.get("required_schema") or {}) else None,
                "error": attempts[-1]["error"] or "; ".join(attempts[-1]["validation_errors"])}
