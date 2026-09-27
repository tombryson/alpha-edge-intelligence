"""Durable single-worker queue for inbound scenario-router announcements."""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional


Processor = Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]
TERMINAL_STATUSES = {"succeeded", "failed"}
RECOVERABLE_STATUSES = {"queued", "processing", "retry_scheduled"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class ScenarioRouterEventQueue:
    """Persist events before processing so a mailbox poll never waits on analysis."""

    def __init__(
        self,
        base_dir: Path,
        *,
        process_timeout_seconds: float = 300.0,
        max_attempts: int = 3,
        retry_delay_seconds: float = 30.0,
    ) -> None:
        self._base_dir = Path(base_dir)
        self._process_timeout_seconds = max(30.0, float(process_timeout_seconds))
        self._max_attempts = max(1, int(max_attempts))
        self._retry_delay_seconds = max(0.01, float(retry_delay_seconds))
        self._processor: Optional[Processor] = None
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._scheduled: set[str] = set()
        self._retry_tasks: set[asyncio.Task[None]] = set()
        self._worker_task: Optional[asyncio.Task[None]] = None

    async def start(self, processor: Processor) -> None:
        self._processor = processor
        self._base_dir.mkdir(parents=True, exist_ok=True)
        for record in self._records():
            status = str(record.get("status") or "").strip().lower()
            if status not in RECOVERABLE_STATUSES:
                continue
            record["status"] = "queued"
            record["recovered_at_utc"] = _utc_now_iso()
            self._write_record(record)
            await self._schedule(str(record.get("event_key") or ""))
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._run(), name="scenario-router-event-queue")

    async def stop(self) -> None:
        if self._worker_task is not None:
            self._worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task
            self._worker_task = None
        for task in list(self._retry_tasks):
            task.cancel()
        for task in list(self._retry_tasks):
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._retry_tasks.clear()
        # The durable records own pending work. Runtime primitives must not retain
        # a previous lifespan's event loop or suppress recovery on the next start.
        self._queue = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._scheduled.clear()

    async def enqueue(self, event_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        key = str(event_key or "").strip()
        if not key:
            raise ValueError("Scenario-router event requires a stable event key.")

        async with self._lock:
            existing = self.get(key)
            if existing:
                status = str(existing.get("status") or "").strip().lower()
                if status in TERMINAL_STATUSES:
                    return {"record": existing, "created": False}
                await self._schedule(key)
                return {"record": existing, "created": False}

            record = {
                "event_key": key,
                "status": "queued",
                "attempts": 0,
                "created_at_utc": _utc_now_iso(),
                "updated_at_utc": _utc_now_iso(),
                "started_at_utc": "",
                "completed_at_utc": "",
                "last_error": "",
                "result": {},
                "payload": dict(payload or {}),
            }
            self._write_record(record)
            await self._schedule(key)
            return {"record": record, "created": True}

    def get(self, event_key: str) -> Dict[str, Any]:
        path = self._record_path(event_key)
        if not path.exists():
            return {}
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return dict(loaded) if isinstance(loaded, dict) else {}

    def list_recent(self, *, limit: int = 50) -> list[Dict[str, Any]]:
        records = self._records()
        records.sort(key=lambda item: str(item.get("updated_at_utc") or ""), reverse=True)
        return [self._public_record(item) for item in records[: max(1, int(limit))]]

    async def _schedule(self, event_key: str) -> None:
        key = str(event_key or "").strip()
        if not key or key in self._scheduled:
            return
        self._scheduled.add(key)
        await self._queue.put(key)

    async def _run(self) -> None:
        while True:
            event_key = await self._queue.get()
            self._scheduled.discard(event_key)
            try:
                await self._process(event_key)
            finally:
                self._queue.task_done()

    async def _process(self, event_key: str) -> None:
        record = self.get(event_key)
        if not record or str(record.get("status") or "").strip().lower() in TERMINAL_STATUSES:
            return
        if self._processor is None:
            return

        record["status"] = "processing"
        record["attempts"] = int(record.get("attempts") or 0) + 1
        record["started_at_utc"] = _utc_now_iso()
        record["updated_at_utc"] = record["started_at_utc"]
        self._write_record(record)
        try:
            result = await asyncio.wait_for(
                self._processor(dict(record.get("payload") or {})),
                timeout=self._process_timeout_seconds,
            )
        except Exception as exc:
            await self._handle_failure(record, str(exc or exc.__class__.__name__))
            return

        record["status"] = "succeeded"
        record["completed_at_utc"] = _utc_now_iso()
        record["updated_at_utc"] = record["completed_at_utc"]
        record["result"] = dict(result or {})
        record["last_error"] = ""
        self._write_record(record)

    async def _handle_failure(self, record: Dict[str, Any], error: str) -> None:
        record["last_error"] = str(error or "Processing failed.")
        record["updated_at_utc"] = _utc_now_iso()
        if int(record.get("attempts") or 0) >= self._max_attempts:
            record["status"] = "failed"
            record["completed_at_utc"] = record["updated_at_utc"]
            self._write_record(record)
            return

        record["status"] = "retry_scheduled"
        self._write_record(record)
        task = asyncio.create_task(self._retry_later(str(record.get("event_key") or "")))
        self._retry_tasks.add(task)
        task.add_done_callback(self._retry_tasks.discard)

    async def _retry_later(self, event_key: str) -> None:
        await asyncio.sleep(self._retry_delay_seconds)
        record = self.get(event_key)
        if str(record.get("status") or "").strip().lower() != "retry_scheduled":
            return
        record["status"] = "queued"
        record["updated_at_utc"] = _utc_now_iso()
        self._write_record(record)
        await self._schedule(event_key)

    def _records(self) -> list[Dict[str, Any]]:
        if not self._base_dir.exists():
            return []
        records: list[Dict[str, Any]] = []
        for path in self._base_dir.glob("*.json"):
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(loaded, dict) and str(loaded.get("event_key") or "").strip():
                records.append(dict(loaded))
        return records

    def _record_path(self, event_key: str) -> Path:
        import hashlib

        digest = hashlib.sha256(str(event_key).encode("utf-8")).hexdigest()
        return self._base_dir / f"{digest}.json"

    def _write_record(self, record: Dict[str, Any]) -> None:
        self._base_dir.mkdir(parents=True, exist_ok=True)
        target = self._record_path(str(record.get("event_key") or ""))
        serialized = json.dumps(record, ensure_ascii=True, indent=2)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self._base_dir, delete=False) as handle:
            handle.write(serialized)
            temporary = Path(handle.name)
        os.replace(temporary, target)

    @staticmethod
    def _public_record(record: Dict[str, Any]) -> Dict[str, Any]:
        return {
            key: value
            for key, value in record.items()
            if key != "payload"
        }
