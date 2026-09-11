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
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    state TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    created REAL NOT NULL,
                    started REAL,
                    updated REAL NOT NULL,
                    completed REAL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    retry_at REAL,
                    source TEXT,
                    destination TEXT,
                    path TEXT,
                    size INTEGER,
                    checksum TEXT,
                    progress REAL NOT NULL DEFAULT 0,
                    error_code TEXT,
                    error_message TEXT,
                    worker_id TEXT,
                    lease_until REAL,
                    parent_job_id TEXT REFERENCES jobs(job_id)
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_claim
                    ON jobs(state, retry_at, priority, created);
                CREATE INDEX IF NOT EXISTS idx_jobs_worker
                    ON jobs(worker_id, lease_until);
                CREATE INDEX IF NOT EXISTS idx_jobs_parent
                    ON jobs(parent_job_id);
                """
            )

    def enqueue(
        self,
        job_type: JobType,
        *,
        priority: str = "NORMAL",
        max_attempts: int = 3,
        source: str | None = None,
        destination: str | None = None,
        path: str | None = None,
        checksum: str | None = None,
        parent_job_id: str | None = None,
        job_id: str | None = None,
    ) -> Job:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        now = time.time()
        job_id = job_id or uuid.uuid4().hex
        with self._connect() as conn:
            if parent_job_id is not None:
                parent = conn.execute("SELECT state FROM jobs WHERE job_id=?", (parent_job_id,)).fetchone()
                if parent is None:
                    raise KeyError(parent_job_id)
                if parent["state"] in (JobState.COMPLETED.value, JobState.FAILED.value, JobState.CANCELLED.value):
                    raise ValueError("cannot add a child to a terminal parent")
            conn.execute(
                """INSERT INTO jobs
                (job_id,type,state,priority,created,updated,max_attempts,source,
                 destination,path,checksum,parent_job_id)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (job_id, job_type.value, JobState.QUEUED.value, priority, now,
                 now, max_attempts, source, destination, path, checksum, parent_job_id),
            )
        return self.get(job_id)

    def get(self, job_id: str) -> Job:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(job_id)
        return self._row(row)

    def children(self, parent_job_id: str) -> list[Job]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE parent_job_id=? ORDER BY created, job_id",
                (parent_job_id,),
            ).fetchall()
        return [self._row(row) for row in rows]

    def child_summary(self, parent_job_id: str) -> ChildSummary:
        children = self.children(parent_job_id)
        counts = {state: 0 for state in JobState}
        for child in children:
            counts[child.state] += 1
        return ChildSummary(
            total=len(children), queued=counts[JobState.QUEUED],
            running=counts[JobState.RUNNING], paused=counts[JobState.PAUSED],
            verifying=counts[JobState.VERIFYING], completed=counts[JobState.COMPLETED],
            failed=counts[JobState.FAILED], cancelled=counts[JobState.CANCELLED],
        )

    def claim(self, worker_id: str, lease_seconds: float = 300) -> Job | None:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        now = time.time()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """SELECT * FROM jobs
                   WHERE state='QUEUED'
                     AND (retry_at IS NULL OR retry_at <= ?)
                   ORDER BY CASE priority
                       WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1
                       WHEN 'NORMAL' THEN 2 WHEN 'LOW' THEN 3
                       ELSE 4 END, created
                   LIMIT 1""",
                (now,),
            ).fetchone()
            if row is None:
                return None
            lease_until = now + lease_seconds
            conn.execute(
                """UPDATE jobs SET state='RUNNING', worker_id=?, lease_until=?,
                   started=COALESCE(started,?), updated=? WHERE job_id=?""",
                (worker_id, lease_until, now, now, row["job_id"]),
            )
        return self.get(row["job_id"])

    def renew_lease(self, job_id: str, worker_id: str, lease_seconds: float = 300) -> Job:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        now = time.time()
        with self._connect() as conn:
            changed = conn.execute(
                """UPDATE jobs SET lease_until=?, updated=?
                   WHERE job_id=? AND worker_id=? AND state='RUNNING'""",
                (now + lease_seconds, now, job_id, worker_id),
            ).rowcount
        if not changed:
            raise ValueError("job is not owned by worker or is not running")
        return self.get(job_id)

    def pause(self, job_id: str, worker_id: str | None = None) -> Job:
        now = time.time()
        with self._connect() as conn:
            if worker_id is None:
                changed = conn.execute(
                    """UPDATE jobs SET state='PAUSED', updated=?, worker_id=NULL,
                       lease_until=NULL WHERE job_id=? AND state='RUNNING'""",
                    (now, job_id),
                ).rowcount
            else:
                changed = conn.execute(
                    """UPDATE jobs SET state='PAUSED', updated=?, worker_id=NULL,
                       lease_until=NULL WHERE job_id=? AND worker_id=? AND state='RUNNING'""",
                    (now, job_id, worker_id),
                ).rowcount
        if not changed:
            raise ValueError("job cannot be paused from its current state or by this worker")
        return self.get(job_id)

    def resume(self, job_id: str) -> Job:
        now = time.time()
        with self._connect() as conn:
            changed = conn.execute(
                """UPDATE jobs SET state='QUEUED', retry_at=NULL, updated=?
                   WHERE job_id=? AND state='PAUSED'""",
                (now, job_id),
            ).rowcount
        if not changed:
            raise ValueError("job cannot be resumed from its current state")
        return self.get(job_id)

    def complete(self, job_id: str, worker_id: str) -> Job:
        now = time.time()
        with self._connect() as conn:
            changed = conn.execute(
                """UPDATE jobs SET state='COMPLETED', progress=1,
                   completed=?, updated=?, lease_until=NULL, worker_id=NULL
                   WHERE job_id=? AND worker_id=? AND state='RUNNING'""",
                (now, now, job_id, worker_id),
            ).rowcount
        if not changed:
            raise ValueError("job cannot be completed by this worker")
        return self.get(job_id)

    def fail(self, job_id: str, worker_id: str, *, error_code: str,
             error_message: str) -> Job:
        now = time.time()
        with self._connect() as conn:
            changed = conn.execute(
                """UPDATE jobs SET state='FAILED', attempts=attempts+1,
                   error_code=?, error_message=?, updated=?, lease_until=NULL,
                   worker_id=NULL WHERE job_id=? AND worker_id=? AND state='RUNNING'""",
                (error_code, error_message, now, job_id, worker_id),
            ).rowcount
        if not changed:
            raise ValueError("job cannot be failed by this worker")
        return self.get(job_id)

    def cancel(self, job_id: str) -> Job:
        now = time.time()
        with self._connect() as conn:
            changed = conn.execute(
                """UPDATE jobs SET state='CANCELLED', updated=?,
                   lease_until=NULL, worker_id=NULL WHERE job_id=?
                   AND state IN ('QUEUED','RUNNING','PAUSED')""",
                (now, job_id),
            ).rowcount
        if not changed:
            raise ValueError("job cannot be cancelled from its current state")
        return self.get(job_id)

    def recover_expired_leases(self) -> int:
        now = time.time()
        with self._connect() as conn:
            result = conn.execute(
                """UPDATE jobs SET state='QUEUED', worker_id=NULL,
                   lease_until=NULL, retry_at=?, updated=?
                   WHERE state='RUNNING' AND lease_until IS NOT NULL
                   AND lease_until < ?""",
                (now, now, now),
            )
            return result.rowcount

    def retry(self, job_id: str, worker_id: str, *, error_code: str,
              error_message: str, delay_seconds: float) -> Job:
        if delay_seconds < 0:
            raise ValueError("delay_seconds must be non-negative")
        now = time.time()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT attempts,max_attempts FROM jobs WHERE job_id=? AND worker_id=? AND state='RUNNING'",
                (job_id, worker_id),
            ).fetchone()
            if row is None:
                raise ValueError("job is not owned by this worker or is not running")
            attempts = row["attempts"] + 1
            if attempts >= row["max_attempts"]:
                state = JobState.FAILED.value
                retry_at = None
            else:
                state = JobState.QUEUED.value
                retry_at = now + delay_seconds
            conn.execute(
                """UPDATE jobs SET attempts=?, state=?, retry_at=?,
                   error_code=?, error_message=?, worker_id=NULL,
                   lease_until=NULL, updated=? WHERE job_id=?""",
                (attempts, state, retry_at, error_code, error_message, now, job_id),
            )
        return self.get(job_id)

    @staticmethod
    def _row(row: sqlite3.Row) -> Job:
        return Job(
            job_id=row["job_id"], type=JobType(row["type"]), state=JobState(row["state"]),
            priority=row["priority"], attempts=row["attempts"], max_attempts=row["max_attempts"],
            retry_at=row["retry_at"], source=row["source"], destination=row["destination"],
            path=row["path"], checksum=row["checksum"], progress=row["progress"],
            error_code=row["error_code"], error_message=row["error_message"],
            worker_id=row["worker_id"], lease_until=row["lease_until"], parent_job_id=row["parent_job_id"],
        )
