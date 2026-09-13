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
from .worker import JobExecutor, Worker


@dataclass(frozen=True)
class ExecutionCapabilities:
    """Deterministic view of which job types have an installed executor."""

    supported: frozenset[JobType]


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
        job: Job | None = None,
        *,
        worker_id: str | None = None,
        audit_conn=None,
        lease_seconds: float = 300,
        authorization_provider=None,
    ) -> Worker:
        """Build the Worker for a claimed job type without moving authority."""
        if job is None:
            raise ValueError("job is required to select a durable executor")
        return Worker(
            store,
            self.executor_for(job.type),
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
        """Claim exactly one job and route it through the registered executor.

        The first queued job determines the executor. The job remains leased by
        Worker and is still subject to the central safety decision before any
        executor is invoked.
        """
        candidate = store.list_jobs(state=None, limit=1000)
        queued = [job for job in candidate if job.state.value == "QUEUED"]
        if not queued:
            return None
        # Do not claim here: Worker.claim owns the authoritative priority/order.
        # Select only after peeking at the same queue through a deterministic
        # read; if another worker races, retry by returning None to the caller.
        selected = min(
            queued,
            key=lambda job: (
                0 if job.priority == "CRITICAL" else 1 if job.priority == "HIGH" else 2 if job.priority == "NORMAL" else 3,
                job.retry_at if job.retry_at is not None else 0,
                job.job_id,
            ),
        )
        return self.worker(
            store,
            selected,
            worker_id=worker_id,
            audit_conn=audit_conn,
            lease_seconds=lease_seconds,
            authorization_provider=authorization_provider,
        ).run_once()
