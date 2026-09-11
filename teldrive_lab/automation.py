"""Stage 6 safe automation primitives built on the existing durable job store."""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .jobs import Job, JobState, JobStore, JobType

MUTATING_TYPES = frozenset({JobType.UPLOAD, JobType.DOWNLOAD, JobType.ARCHIVE, JobType.BACKUP,
                            JobType.SNAPSHOT, JobType.ORGANIZE, JobType.CLEANUP, JobType.RESTORE})
HIGH_RISK_TYPES = frozenset({JobType.CLEANUP, JobType.RESTORE, JobType.ORGANIZE})


@dataclass(frozen=True, slots=True)
class Schedule:
    schedule_id: str
    job_type: JobType
    interval_seconds: int
    next_run: float
    enabled: bool


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_automation_db(path: Path) -> None:
    with _connect(path) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS schedules (
            schedule_id TEXT PRIMARY KEY, job_type TEXT NOT NULL,
            interval_seconds INTEGER NOT NULL, next_run REAL NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1, source TEXT, destination TEXT, path TEXT
        );
        CREATE TABLE IF NOT EXISTS approvals (
            approval_id TEXT PRIMARY KEY, operation TEXT NOT NULL, job_id TEXT,
            status TEXT NOT NULL, requested REAL NOT NULL, decided REAL, reason TEXT
        );
        CREATE TABLE IF NOT EXISTS inbound_events (
            event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL,
            received REAL NOT NULL, payload_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_schedules_due ON schedules(enabled, next_run);
        """)


def create_schedule(path: Path, job_type: JobType, *, interval_seconds: int,
                    start_at: float | None = None, schedule_id: str | None = None,
                    source: str | None = None, destination: str | None = None,
                    job_path: str | None = None) -> Schedule:
    if interval_seconds < 1:
        raise ValueError("interval_seconds must be positive")
    schedule = Schedule(schedule_id or uuid.uuid4().hex, job_type, interval_seconds,
                        time.time() if start_at is None else start_at, True)
    init_automation_db(path)
    with _connect(path) as conn:
        conn.execute("INSERT INTO schedules VALUES (?,?,?,?,?,?,?,?)",
                     (schedule.schedule_id, job_type.value, interval_seconds, schedule.next_run, 1,
                      source, destination, job_path))
    return schedule


def due_schedules(path: Path, *, now: float | None = None) -> list[Schedule]:
    init_automation_db(path)
    stamp = time.time() if now is None else now
    with _connect(path) as conn:
        rows = conn.execute("SELECT * FROM schedules WHERE enabled=1 AND next_run<=? ORDER BY next_run, schedule_id", (stamp,)).fetchall()
    return [Schedule(r["schedule_id"], JobType(r["job_type"]), r["interval_seconds"], r["next_run"], bool(r["enabled"])) for r in rows]


def materialize_due_schedule(path: Path, schedule_id: str, jobs: JobStore, *, now: float | None = None) -> Job:
    stamp = time.time() if now is None else now
    init_automation_db(path)
    with _connect(path) as conn:
        row = conn.execute("SELECT * FROM schedules WHERE schedule_id=? AND enabled=1 AND next_run<=?", (schedule_id, stamp)).fetchone()
        if row is None:
            raise ValueError("schedule is not due or disabled")
        job = jobs.enqueue(JobType(row["job_type"]), source=row["source"], destination=row["destination"], path=row["path"])
        conn.execute("UPDATE schedules SET next_run=? WHERE schedule_id=?", (stamp + row["interval_seconds"], schedule_id))
    return job


def ingest_event(path: Path, event_type: str, payload: dict[str, Any], *, event_id: str | None = None) -> str:
    if not event_type.strip():
        raise ValueError("event_type is required")
    eid = event_id or uuid.uuid4().hex
    init_automation_db(path)
    with _connect(path) as conn:
        conn.execute("INSERT INTO inbound_events VALUES (?,?,?,?)", (eid, event_type, time.time(), json.dumps(payload, sort_keys=True)))
    return eid


def dependency_ready(jobs: JobStore, job: Job) -> bool:
    if job.parent_job_id is None:
        return True
    parent = jobs.get(job.parent_job_id)
    return parent.state is JobState.COMPLETED


def verification_required(job_type: JobType) -> bool:
    return job_type in MUTATING_TYPES


def verification_plan(job: Job) -> dict[str, Any]:
    required = verification_required(job.type)
    return {"job_id": job.job_id, "required": required,
            "verification_job_type": JobType.VERIFY.value if required else None,
            "rule": "mutation must not be considered complete until verification succeeds" if required else "no mutation verification required"}


def approval_required(job_type: JobType) -> bool:
    return job_type in HIGH_RISK_TYPES


def request_approval(path: Path, operation: str, *, job_id: str | None = None) -> str:
    if not operation.strip():
        raise ValueError("operation is required")
    init_automation_db(path)
    aid = uuid.uuid4().hex
    with _connect(path) as conn:
        conn.execute("INSERT INTO approvals VALUES (?,?,?,?,?,?,?)", (aid, operation, job_id, "PENDING", time.time(), None, None))
    return aid


def decide_approval(path: Path, approval_id: str, *, approved: bool, reason: str) -> None:
    init_automation_db(path)
    with _connect(path) as conn:
        changed = conn.execute("UPDATE approvals SET status=?, decided=?, reason=? WHERE approval_id=? AND status='PENDING'",
                               ("APPROVED" if approved else "DENIED", time.time(), reason, approval_id)).rowcount
    if not changed:
        raise ValueError("approval is missing or already decided")


def approval_status(path: Path, approval_id: str) -> str:
    init_automation_db(path)
    with _connect(path) as conn:
        row = conn.execute("SELECT status FROM approvals WHERE approval_id=?", (approval_id,)).fetchone()
    if row is None:
        raise KeyError(approval_id)
    return str(row["status"])


def webhook_payload(event_type: str, *, job_id: str | None = None, result: str | None = None) -> dict[str, Any]:
    if not event_type.strip():
        raise ValueError("event_type is required")
    return {"version": 1, "type": event_type, "job_id": job_id, "result": result}


def local_notification(path: Path, title: str, message: str) -> Path:
    """Write a local notification spool entry; no network or paid service is used."""
    if not title.strip() or not message.strip():
        raise ValueError("title and message are required")
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {"timestamp": time.time(), "title": title, "message": message}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
    return path


def degraded_action(provider_state: str) -> str:
    normalized = provider_state.strip().upper()
    if normalized in {"DEGRADED", "UNAVAILABLE", "UNKNOWN"}:
        return "PAUSE_AND_RETRY"
    return "CONTINUE"


__all__ = [name for name in globals() if not name.startswith("_")]
