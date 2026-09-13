"""R4 unified durable execution registry.

The registry is the single selection point for durable job executors. It does
not authorize operations and it does not bypass Worker/JobStore; all execution
still crosses the existing safety boundary and durable lease lifecycle.
"""

from __future__ import annotations

from dataclasses import dataclass

from .archive import ArchiveJobExecutor
from .jobs import Job, JobType, JobStore
from .organization import OrganizationJobExecutor
from .transfer import TransferManager
from .transfer_executor import TransferJobExecutor
from .worker import ExecutionResult, JobExecutor, Worker
from .safety import AuthorizationReceipt


@dataclass(frozen=True)
class ExecutionCapabilities:
    """Deterministic view of which job types have an installed executor."""

    supported: frozenset[JobType]


class DispatchingExecutor:
    """One Worker-facing executor that routes by the durable job type."""

    def __init__(self, executors: dict[JobType, JobExecutor]) -> None:
        self._executors = dict(executors)

    def execute(self, job: Job, authorization: AuthorizationReceipt | None = None) -> ExecutionResult:
        executor = self._executors.get(job.type)
        if executor is None:
            from .worker import ExecutionStatus
            return ExecutionResult(
                ExecutionStatus.PERMANENT,
                "UNSUPPORTED_JOB_TYPE",
                f"no durable executor registered for {job.type.value}",
            )
        return executor.execute(job, authorization)


class DurableExecutionRegistry:
    """Central executor registry for all durable execution entry points."""

    def __init__(self, *, transfer_manager: TransferManager | None = None) -> None:
        manager = transfer_manager or TransferManager()
        self._executors: dict[JobType, JobExecutor] = {
            JobType.UPLOAD: TransferJobExecutor(manager),
            JobType.DOWNLOAD: TransferJobExecutor(manager),
            JobType.ARCHIVE: ArchiveJobExecutor(manager),
            JobType.ORGANIZE: OrganizationJobExecutor(manager),
        }
        self.dispatcher = DispatchingExecutor(self._executors)

    @property
    def capabilities(self) -> ExecutionCapabilities:
        return ExecutionCapabilities(frozenset(self._executors))

    def executor_for(self, job_type: JobType) -> JobExecutor:
        try:
            return self._executors[job_type]
        except KeyError as exc:
            raise ValueError(f"no durable executor registered for {job_type.value}") from exc

    def worker(
        self,
        store: JobStore,
        *,
        worker_id: str | None = None,
        audit_conn=None,
        lease_seconds: float = 300,
        authorization_provider=None,
    ) -> Worker:
        """Build the single Worker boundary for every registered job type."""
        return Worker(
            store,
            self.dispatcher,
            worker_id=worker_id,
            audit_conn=audit_conn,
            lease_seconds=lease_seconds,
            authorization_provider=authorization_provider,
        )

    def run_once(
        self,
        store: JobStore,
        *,
        worker_id: str | None = None,
        audit_conn=None,
        lease_seconds: float = 300,
        authorization_provider=None,
    ) -> Job | None:
        """Claim and execute exactly one queued job through the central boundary."""
        return self.worker(
            store,
            worker_id=worker_id,
            audit_conn=audit_conn,
            lease_seconds=lease_seconds,
            authorization_provider=authorization_provider,
        ).run_once()
