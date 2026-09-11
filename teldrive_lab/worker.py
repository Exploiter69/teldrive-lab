"""Phase 3 durable worker boundary.

The worker coordinates durable jobs but never becomes an authorization source.
Actual side effects are delegated to an executor after the deterministic safety
policy has approved the job's operation and paths.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .audit import record_event
from .jobs import Job, JobState, JobStore
from .safety import Operation, authorize


class ExecutionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    RETRYABLE = "RETRYABLE"
    PERMANENT = "PERMANENT"
    UNSAFE = "UNSAFE"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class ExecutionResult:
    status: ExecutionStatus
    error_code: str | None = None
    error_message: str | None = None
    delay_seconds: float = 0.0


class JobExecutor(Protocol):
    """Narrow side-effect boundary implemented by concrete executors."""

    def execute(self, job: Job) -> ExecutionResult:
        ...


class Worker:
    """Claim and coordinate one durable job without self-authorizing it."""

    def __init__(self, store: JobStore, executor: JobExecutor, *, worker_id: str | None = None,
                 audit_conn=None, lease_seconds: float = 300) -> None:
        self.store = store
        self.executor = executor
        self.worker_id = worker_id or uuid.uuid4().hex
        self.audit_conn = audit_conn
        self.lease_seconds = lease_seconds

    def run_once(self) -> Job | None:
        job = self.store.claim(self.worker_id, self.lease_seconds)
        if job is None:
            return None

        self._audit("worker.claim", job, "ALLOWED", "CLAIMED")
        decision = self._safety_decision(job)
        if not decision.allowed:
            self._audit("worker.safety_gate", job, "DENIED", "BLOCKED",
                        error_code="UNSAFE_OPERATION", details={"reason": decision.reason})
            failed = self.store.fail(job.job_id, self.worker_id,
                                     error_code="UNSAFE_OPERATION",
                                     error_message=decision.reason)
            self._audit("worker.failure", failed, "DENIED", "FAILED",
                        error_code="UNSAFE_OPERATION")
            return failed

        self._audit("worker.safety_gate", job, "ALLOWED", "APPROVED")
        try:
            result = self.executor.execute(job)
        except Exception as exc:
            result = ExecutionResult(ExecutionStatus.RETRYABLE,
                                     error_code="EXECUTOR_EXCEPTION",
                                     error_message=str(exc))

        # Cancellation/pause may be requested cooperatively while an executor is
        # running. Once the durable state leaves RUNNING, the worker must not
        # overwrite that control decision with a completion/failure transition.
        current = self.store.get(job.job_id)
        if current.state is not JobState.RUNNING or current.worker_id != self.worker_id:
            self._audit(
                "worker.control_race", current, "ALLOWED", current.state.value,
                details={"execution_status": result.status.value},
            )
            return current

        if result.status is ExecutionStatus.SUCCESS:
            completed = self.store.complete(job.job_id, self.worker_id)
            self._audit("worker.complete", completed, "ALLOWED", "COMPLETED")
            return completed

        if result.status is ExecutionStatus.CANCELLED:
            cancelled = self.store.cancel(job.job_id)
            self._audit("worker.cancel", cancelled, "ALLOWED", "CANCELLED")
            return cancelled

        if result.status is ExecutionStatus.RETRYABLE:
            retried = self.store.retry(
                job.job_id, self.worker_id,
                error_code=result.error_code or "RETRYABLE",
                error_message=result.error_message or "retryable execution failure",
                delay_seconds=max(0, result.delay_seconds),
            )
            self._audit("worker.retry", retried, "ALLOWED", retried.state.value,
                        error_code=retried.error_code)
            return retried

        if result.status in (ExecutionStatus.PERMANENT, ExecutionStatus.UNSAFE):
            failed = self.store.fail(
                job.job_id, self.worker_id,
                error_code=result.error_code or result.status.value,
                error_message=result.error_message or "execution failed",
            )
            self._audit("worker.failure", failed, "ALLOWED", "FAILED",
                        error_code=failed.error_code)
            return failed

        raise RuntimeError(f"unsupported execution status: {result.status}")

    @staticmethod
    def _operation_for(job: Job) -> Operation:
        if job.type.value == "INDEX":
            return Operation.INDEX
        if job.type.value == "VERIFY":
            return Operation.VERIFY
        return Operation.TRANSFER

    def _safety_decision(self, job: Job):
        paths = [p for p in (job.source, job.destination, job.path) if p]
        # A worker never supplies explicit authorization. A queued job or lease
        # is not authorization; a higher-level control surface must provide it.
        return authorize(self._operation_for(job), *paths)

    def _audit(self, operation: str, job: Job, decision: str, result: str, *,
               error_code: str | None = None, details: dict | None = None) -> None:
        if self.audit_conn is None:
            return
        record_event(self.audit_conn, event_id=uuid.uuid4().hex, operation=operation,
                     job_id=job.job_id, source=job.source, destination=job.destination,
                     decision=decision, result=result, error_code=error_code,
                     details=details)
