"""Durable Phase 3 job primitives backed by SQLite."""

from __future__ import annotations

import sqlite3
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class JobState(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobType(str, Enum):
    UPLOAD = "UPLOAD"
    DOWNLOAD = "DOWNLOAD"
    ARCHIVE = "ARCHIVE"
    VERIFY = "VERIFY"
    BACKUP = "BACKUP"
    SNAPSHOT = "SNAPSHOT"
    ORGANIZE = "ORGANIZE"
    CLEANUP = "CLEANUP"
    INDEX = "INDEX"
    RESTORE = "RESTORE"


@dataclass(frozen=True)
class Job:
    job_id: str
    type: JobType
    state: JobState
    priority: str
    attempts: int
    max_attempts: int
    retry_at: float | None
    source: str | None
    destination: str | None
    path: str | None
    checksum: str | None
    progress: float
    error_code: str | None
    error_message: str | None
    worker_id: str | None
    lease_until: float | None
    parent_job_id: str | None
    idempotency_key: str | None = None


@dataclass(frozen=True)
class ChildSummary:
    total: int
    queued: int
    running: int
    paused: int
    verifying: int
    completed: int
    failed: int
    cancelled: int

    @property
    def terminal(self) -> bool:
        return self.total > 0 and self.completed + self.failed + self.cancelled == self.total

    @property
    def successful(self) -> bool:
        return self.terminal and self.completed == self.total


class JobStore:
    """Small durable queue store; it never performs the job itself."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY, type TEXT NOT NULL, state TEXT NOT NULL,
                priority TEXT NOT NULL, created REAL NOT NULL, started REAL,
                updated REAL NOT NULL, completed REAL, attempts INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 3, retry_at REAL, source TEXT,
                destination TEXT, path TEXT, size INTEGER, checksum TEXT,
                progress REAL NOT NULL DEFAULT 0, error_code TEXT, error_message TEXT,
                worker_id TEXT, lease_until REAL, parent_job_id TEXT REFERENCES jobs(job_id),
                idempotency_key TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_jobs_claim ON jobs(state, retry_at, priority, created);
            CREATE INDEX IF NOT EXISTS idx_jobs_worker ON jobs(worker_id, lease_until);
            CREATE INDEX IF NOT EXISTS idx_jobs_parent ON jobs(parent_job_id);
            """)
            columns = {row[1] for row in conn.execute("PRAGMA table_info(jobs)")}
            if "idempotency_key" not in columns:
                conn.execute("ALTER TABLE jobs ADD COLUMN idempotency_key TEXT")
                rows = conn.execute("SELECT job_id,type,source,destination,path,checksum FROM jobs WHERE idempotency_key IS NULL").fetchall()
                for row in rows:
                    key = self._idempotency_key(JobType(row[1]), row[2], row[3], row[4], row[5])
                    conn.execute("UPDATE jobs SET idempotency_key=? WHERE job_id=?", (key, row[0]))
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_idempotency ON jobs(idempotency_key)")

    def enqueue(self, job_type: JobType, *, priority: str = "NORMAL", max_attempts: int = 3,
                source: str | None = None, destination: str | None = None, path: str | None = None,
                checksum: str | None = None, parent_job_id: str | None = None, job_id: str | None = None,
                idempotency_key: str | None = None) -> Job:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        now = time.time(); job_id = job_id or uuid.uuid4().hex
        idempotency_key = idempotency_key or self._idempotency_key(job_type, source, destination, path, checksum)
        with self._connect() as conn:
            if parent_job_id is not None:
                parent = conn.execute("SELECT state FROM jobs WHERE job_id=?", (parent_job_id,)).fetchone()
                if parent is None:
                    raise KeyError(parent_job_id)
                if parent["state"] in (JobState.COMPLETED.value, JobState.FAILED.value, JobState.CANCELLED.value):
                    raise ValueError("cannot add a child to a terminal parent")
            conn.execute("""INSERT INTO jobs
                (job_id,type,state,priority,created,updated,max_attempts,source,destination,path,checksum,parent_job_id,idempotency_key)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                         (job_id, job_type.value, JobState.QUEUED.value, priority, now, now, max_attempts,
                          source, destination, path, checksum, parent_job_id, idempotency_key))
        return self.get(job_id)

    def get(self, job_id: str) -> Job:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(job_id)
        return self._row(row)

    def list_jobs(self, *, state: JobState | None = None, limit: int = 100) -> list[Job]:
        """Read-only deterministic job listing for operators."""
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        with self._connect() as conn:
            if state is None:
                rows = conn.execute("SELECT * FROM jobs ORDER BY created DESC, job_id LIMIT ?", (limit,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM jobs WHERE state=? ORDER BY created DESC, job_id LIMIT ?", (state.value, limit)).fetchall()
        return [self._row(row) for row in rows]

    def children(self, parent_job_id: str) -> list[Job]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM jobs WHERE parent_job_id=? ORDER BY created, job_id", (parent_job_id,)).fetchall()
        return [self._row(row) for row in rows]

    def child_summary(self, parent_job_id: str) -> ChildSummary:
        children = self.children(parent_job_id); counts = {state: 0 for state in JobState}
        for child in children: counts[child.state] += 1
        return ChildSummary(total=len(children), queued=counts[JobState.QUEUED], running=counts[JobState.RUNNING], paused=counts[JobState.PAUSED], verifying=counts[JobState.VERIFYING], completed=counts[JobState.COMPLETED], failed=counts[JobState.FAILED], cancelled=counts[JobState.CANCELLED])

    @property
    def _unused(self):
        return None

    def claim(self, worker_id: str, lease_seconds: float = 300) -> Job | None:
        if lease_seconds <= 0: raise ValueError("lease_seconds must be positive")
        now = time.time()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("""SELECT * FROM jobs WHERE state='QUEUED' AND (retry_at IS NULL OR retry_at <= ?)
                ORDER BY CASE priority WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1 WHEN 'NORMAL' THEN 2 WHEN 'LOW' THEN 3 ELSE 4 END, created LIMIT 1""", (now,)).fetchone()
            if row is None: return None
            conn.execute("UPDATE jobs SET state='RUNNING', worker_id=?, lease_until=?, started=COALESCE(started,?), updated=? WHERE job_id=?", (worker_id, now + lease_seconds, now, now, row["job_id"]))
        return self.get(row["job_id"])

    def renew_lease(self, job_id: str, worker_id: str, lease_seconds: float = 300) -> Job:
        if lease_seconds <= 0: raise ValueError("lease_seconds must be positive")
        now = time.time()
        with self._connect() as conn:
            changed = conn.execute("UPDATE jobs SET lease_until=?, updated=? WHERE job_id=? AND worker_id=? AND state='RUNNING'", (now + lease_seconds, now, job_id, worker_id)).rowcount
        if not changed: raise ValueError("job is not owned by worker or is not running")
        return self.get(job_id)

    def pause(self, job_id: str, worker_id: str | None = None) -> Job:
        now = time.time()
        with self._connect() as conn:
            if worker_id is None:
                changed = conn.execute("UPDATE jobs SET state='PAUSED', updated=?, worker_id=NULL, lease_until=NULL WHERE job_id=? AND state='RUNNING'", (now, job_id)).rowcount
            else:
                changed = conn.execute("UPDATE jobs SET state='PAUSED', updated=?, worker_id=NULL, lease_until=NULL WHERE job_id=? AND worker_id=? AND state='RUNNING'", (now, job_id, worker_id)).rowcount
        if not changed: raise ValueError("job cannot be paused from its current state or by this worker")
        return self.get(job_id)

    def resume(self, job_id: str) -> Job:
        now = time.time()
        with self._connect() as conn:
            changed = conn.execute("UPDATE jobs SET state='QUEUED', retry_at=NULL, updated=? WHERE job_id=? AND state='PAUSED'", (now, job_id)).rowcount
        if not changed: raise ValueError("job cannot be resumed from its current state")
        return self.get(job_id)

    def complete(self, job_id: str, worker_id: str) -> Job:
        now = time.time()
        with self._connect() as conn:
            changed = conn.execute("UPDATE jobs SET state='COMPLETED', progress=1, completed=?, updated=?, lease_until=NULL, worker_id=NULL WHERE job_id=? AND worker_id=? AND state='RUNNING'", (now, now, job_id, worker_id)).rowcount
        if not changed: raise ValueError("job cannot be completed by this worker")
        return self.get(job_id)

    def fail(self, job_id: str, worker_id: str, *, error_code: str, error_message: str) -> Job:
        now = time.time()
        with self._connect() as conn:
            changed = conn.execute("UPDATE jobs SET state='FAILED', attempts=attempts+1, error_code=?, error_message=?, updated=?, lease_until=NULL, worker_id=NULL WHERE job_id=? AND worker_id=? AND state='RUNNING'", (error_code, error_message, now, job_id, worker_id)).rowcount
        if not changed: raise ValueError("job cannot be failed by this worker")
        return self.get(job_id)

    def cancel(self, job_id: str) -> Job:
        now = time.time()
        with self._connect() as conn:
            changed = conn.execute("UPDATE jobs SET state='CANCELLED', updated=?, lease_until=NULL, worker_id=NULL WHERE job_id=? AND state IN ('QUEUED','RUNNING','PAUSED')", (now, job_id)).rowcount
        if not changed: raise ValueError("job cannot be cancelled from its current state")
        return self.get(job_id)

    def expired_running_jobs(self, *, now: float | None = None) -> list[Job]:
        now = time.time() if now is None else now
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE state='RUNNING' AND lease_until IS NOT NULL AND lease_until < ? ORDER BY created, job_id",
                (now,),
            ).fetchall()
        return [self._row(row) for row in rows]

    def recover_expired_leases(self, reconciler=None) -> int:
        """Recover expired jobs only after external-state reconciliation."""
        if reconciler is None:
            return 0
        now = time.time()
        recovered = 0
        for job in self.expired_running_jobs(now=now):
            decision = reconciler(job)
            action = getattr(decision, "action", None)
            reason = getattr(decision, "reason", "recovery decision missing reason")
            with self._connect() as conn:
                if action == "COMPLETE":
                    changed = conn.execute(
                        "UPDATE jobs SET state='COMPLETED', progress=1, completed=?, updated=?, worker_id=NULL, lease_until=NULL WHERE job_id=? AND state='RUNNING' AND lease_until < ?",
                        (now, now, job.job_id, now),
                    ).rowcount
                elif action == "REQUEUE":
                    changed = conn.execute(
                        "UPDATE jobs SET state='QUEUED', retry_at=?, updated=?, worker_id=NULL, lease_until=NULL WHERE job_id=? AND state='RUNNING' AND lease_until < ?",
                        (now, now, job.job_id, now),
                    ).rowcount
                else:
                    changed = conn.execute(
                        "UPDATE jobs SET state='FAILED', attempts=attempts+1, error_code='RECOVERY_RECONCILIATION', error_message=?, updated=?, worker_id=NULL, lease_until=NULL WHERE job_id=? AND state='RUNNING' AND lease_until < ?",
                        (reason, now, job.job_id, now),
                    ).rowcount
                recovered += changed
        return recovered

    def retry(self, job_id: str, worker_id: str, *, error_code: str, error_message: str, delay_seconds: float) -> Job:
        if delay_seconds < 0: raise ValueError("delay_seconds must be non-negative")
        now = time.time()
        with self._connect() as conn:
            row = conn.execute("SELECT attempts,max_attempts FROM jobs WHERE job_id=? AND worker_id=? AND state='RUNNING'", (job_id, worker_id)).fetchone()
            if row is None: raise ValueError("job is not owned by this worker or is not running")
            attempts = row["attempts"] + 1
            state = JobState.FAILED.value if attempts >= row["max_attempts"] else JobState.QUEUED.value
            retry_at = None if state == JobState.FAILED.value else now + delay_seconds
            conn.execute("UPDATE jobs SET attempts=?, state=?, retry_at=?, error_code=?, error_message=?, worker_id=NULL, lease_until=NULL, updated=? WHERE job_id=?", (attempts, state, retry_at, error_code, error_message, now, job_id))
        return self.get(job_id)

    @staticmethod
    def _idempotency_key(job_type: JobType, source: str | None, destination: str | None, path: str | None, checksum: str | None) -> str:
        import hashlib
        payload = "\x1f".join([job_type.value, source or "", destination or "", path or "", checksum or ""])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _row(row: sqlite3.Row) -> Job:
        return Job(job_id=row["job_id"], type=JobType(row["type"]), state=JobState(row["state"]), priority=row["priority"], attempts=row["attempts"], max_attempts=row["max_attempts"], retry_at=row["retry_at"], source=row["source"], destination=row["destination"], path=row["path"], checksum=row["checksum"], progress=row["progress"], error_code=row["error_code"], error_message=row["error_message"], worker_id=row["worker_id"], lease_until=row["lease_until"], parent_job_id=row["parent_job_id"], idempotency_key=row["idempotency_key"] if "idempotency_key" in row.keys() else None)
