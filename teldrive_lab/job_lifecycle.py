"""Audited job lifecycle and reconciliation helpers.

This module composes the durable JobStore with the existing audit log. It does
not execute storage work and does not grant authorization.
"""

from __future__ import annotations

import hashlib
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .audit import open_audit, record_event
from .jobs import Job, JobStore, JobType


@dataclass(frozen=True)
class Reconciliation:
    """Result of comparing intended work with an observed outcome."""

    safe_to_execute: bool
    reason: str


def idempotency_key(*parts: str | None) -> str:
    """Return a stable, non-secret key for the same logical operation."""
    payload = "\x1f".join("" if part is None else part for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def reconcile(*, intended_checksum: str | None, observed_checksum: str | None,
               observed_exists: bool) -> Reconciliation:
    """Never claim completion without an observation that proves it."""
    if not observed_exists:
        return Reconciliation(True, "no matching completed artifact observed")
    if intended_checksum and observed_checksum:
        if intended_checksum == observed_checksum:
            return Reconciliation(False, "matching checksum already observed")
        return Reconciliation(False, "existing artifact has a different checksum")
    return Reconciliation(False, "existing artifact cannot be safely identified")


class AuditedJobStore:
    """JobStore facade that emits an audit event for each lifecycle action."""

    def __init__(self, jobs_path: Path, audit_path: Path):
        self.jobs = JobStore(jobs_path)
        self.audit_path = Path(audit_path)

    def _audit(self, *, operation: str, job: Job, decision: str,
               result: str | None = None, error_code: str | None = None,
               details: dict | None = None) -> None:
        conn = open_audit(self.audit_path)
        try:
            record_event(
                conn,
                event_id=uuid.uuid4().hex,
                operation=operation,
                decision=decision,
                result=result,
                job_id=job.job_id,
                source=job.source,
                destination=job.destination,
                checksum=job.checksum,
                error_code=error_code,
                details=details,
            )
        finally:
            conn.close()

    def enqueue(self, job_type: JobType, **kwargs) -> Job:
        job = self.jobs.enqueue(job_type, **kwargs)
        self._audit(operation="JOB_ENQUEUE", job=job, decision="ALLOW", result="QUEUED")
        return job

    def claim(self, worker_id: str, lease_seconds: float = 300) -> Job | None:
        job = self.jobs.claim(worker_id, lease_seconds)
        if job is not None:
            self._audit(
                operation="JOB_CLAIM", job=job, decision="ALLOW", result="RUNNING",
                details={"worker_id": worker_id, "lease_seconds": lease_seconds},
            )
        return job

    def complete(self, job_id: str, worker_id: str) -> Job:
        job = self.jobs.complete(job_id, worker_id)
        self._audit(operation="JOB_COMPLETE", job=job, decision="ALLOW", result="COMPLETED")
        return job

    def cancel(self, job_id: str) -> Job:
        job = self.jobs.cancel(job_id)
        self._audit(operation="JOB_CANCEL", job=job, decision="ALLOW", result="CANCELLED")
        return job

    def retry(self, job_id: str, worker_id: str, *, error_code: str,
              error_message: str, delay_seconds: float) -> Job:
        job = self.jobs.retry(
            job_id, worker_id, error_code=error_code,
            error_message=error_message, delay_seconds=delay_seconds,
        )
        self._audit(
            operation="JOB_RETRY", job=job, decision="ALLOW", result=job.state.value,
            error_code=error_code,
            details={"delay_seconds": delay_seconds},
        )
        return job

    def recover_expired_leases(self) -> int:
        count = self.jobs.recover_expired_leases()
        if count:
            # Recovery is an operational event without a single job identity.
            conn = open_audit(self.audit_path)
            try:
                record_event(
                    conn, event_id=uuid.uuid4().hex, operation="JOB_LEASE_RECOVERY",
                    decision="ALLOW", result="REQUEUED", details={"count": count},
                )
            finally:
                conn.close()
        return count
