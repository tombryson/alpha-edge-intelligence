"""Durable submission identity. A reserved ID is never automatically re-executed."""

import hashlib
import json
import sqlite3
import uuid

from fastapi import HTTPException

from . import state


def submission_id(value):
    if not value:
        return None  # Existing Intelligence clients remain compatible.
    try:
        return str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(400, detail="Idempotency-Key must be a UUID") from exc


async def fingerprint(payload, upload=None):
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())
    if upload is not None:
        digest.update((upload.filename or "").encode())
        while chunk := await upload.read(1024 * 1024):
            digest.update(chunk)
        await upload.seek(0)
    return digest.hexdigest()


def _connect():
    state.JOBS_META_DIR.mkdir(parents=True, exist_ok=True)
    path = state.JOBS_META_DIR / "submissions.sqlite"
    connection = sqlite3.connect(path, timeout=15)
    path.chmod(0o600)
    connection.execute("PRAGMA synchronous=FULL")
    connection.execute("CREATE TABLE IF NOT EXISTS submissions (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, job_id TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    return connection


def lookup(key, expected=None):
    connection = _connect()
    try:
        row = connection.execute("SELECT fingerprint, job_id FROM submissions WHERE id=?", (key,)).fetchone()
    finally:
        connection.close()
    if row and expected and row[0] != expected:
        raise HTTPException(409, detail="Submission ID already belongs to a different request")
    return row[1] if row else None


def reserve(key, digest, job_id):
    connection = _connect()
    try:
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT fingerprint, job_id FROM submissions WHERE id=?", (key,)).fetchone()
            if row:
                if row[0] != digest:
                    raise HTTPException(409, detail="Submission ID already belongs to a different request")
                return row[1], False
            connection.execute("INSERT INTO submissions(id,fingerprint,job_id) VALUES(?,?,?)", (key, digest, job_id))
        return job_id, True
    finally:
        connection.close()


def read_job(job_id):
    path = state.JOBS_META_DIR / f"{job_id}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
