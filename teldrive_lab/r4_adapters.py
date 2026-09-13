"""R4 durable adapters for backup, lifecycle, verification, and rclone.

These adapters are intentionally thin: Worker/JobStore remain the durable
authority, while domain executors remain responsible for their existing
safety and verification contracts. No adapter writes TelDrive state directly.
"""

from __future__ import annotations

import json
from pathlib import Path

from .backups import BackupExecutor, BackupPlanner, BackupStore
from .jobs import Job, JobType
from .lifecycle import LifecycleExecutor, LifecyclePlanner, LifecycleStore
from .rclone import RcloneAdapter
from .safety import AuthorizationReceipt, Operation
from .transfer import TransferBackend, TransferManager, TransferResult, TransferSpec, sha256_file
from .worker import ExecutionResult, ExecutionStatus


class BackupJobExecutor:
    """Durably execute a BACKUP job through the existing BackupExecutor."""

    def __init__(self, *, store: BackupStore | None = None, transfer: TransferManager | None = None) -> None:
        self.store = store or BackupStore()
        self.transfer = transfer or TransferManager()
        self.domain = BackupExecutor(self.store, self.transfer)

    def execute(self, job: Job, authorization: AuthorizationReceipt | None = None) -> ExecutionResult:
        if job.type not in (JobType.BACKUP, JobType.SNAPSHOT):
            return ExecutionResult(ExecutionStatus.PERMANENT, "WRONG_JOB_TYPE", "backup executor received another job type")
        if not authorization:
            return ExecutionResult(ExecutionStatus.UNSAFE, "AUTHORIZATION_REQUIRED", "backup execution requires an authorization receipt")
        if not job.source or not job.destination:
            return ExecutionResult(ExecutionStatus.PERMANENT, "BACKUP_INPUT", "backup job requires source and destination")
        try:
            sources = tuple(json.loads(job.source))
            if not sources or not all(isinstance(item, str) for item in sources):
                raise ValueError("source must be a non-empty JSON string list")
            planner = BackupPlanner()
            plan = planner.snapshot_plan(sources, snapshot_root=job.destination) if job.type is JobType.SNAPSHOT else planner.plan(sources, backup_root=job.destination)
            ok, _ = self.domain.apply(plan, authorization_id=authorization.authorization_id)
            if not ok:
                return ExecutionResult(ExecutionStatus.RETRYABLE, "BACKUP_FAILED", "backup transfer or verification failed", 1.0)
            return ExecutionResult(ExecutionStatus.SUCCESS)
        except (ValueError, FileNotFoundError, PermissionError) as exc:
            return ExecutionResult(ExecutionStatus.PERMANENT, "BACKUP_INPUT", str(exc))
        except OSError as exc:
            return ExecutionResult(ExecutionStatus.RETRYABLE, "BACKUP_IO", str(exc), 1.0)


class LifecycleJobExecutor:
    """Durably execute conservative lifecycle transfers/restores."""

    def __init__(self, *, store: LifecycleStore | None = None, transfer: TransferManager | None = None) -> None:
        self.store = store or LifecycleStore()
        self.transfer = transfer or TransferManager()
        self.domain = LifecycleExecutor(self.store, self.transfer)

    def execute(self, job: Job, authorization: AuthorizationReceipt | None = None) -> ExecutionResult:
        if not authorization:
            return ExecutionResult(ExecutionStatus.UNSAFE, "AUTHORIZATION_REQUIRED", "lifecycle execution requires an authorization receipt")
        if not job.source or not job.destination:
            return ExecutionResult(ExecutionStatus.PERMANENT, "LIFECYCLE_INPUT", "lifecycle job requires source and destination")
        try:
            planner = LifecyclePlanner(self.store)
            if job.type is JobType.RESTORE:
                plan = planner.restore_plan(destination_root=job.destination, sources=(job.source,))
                if any(item.action.name == "PURGE_BLOCKED" for item in plan.items):
                    return ExecutionResult(ExecutionStatus.PERMANENT, "RESTORE_PLAN_BLOCKED", "lifecycle restore plan is blocked")
                ok, _ = self.domain.restore(plan, authorization_id=authorization.authorization_id)
            elif job.type is JobType.CLEANUP:
                plan = planner.quarantine_plan((job.source,), quarantine_root=job.destination)
                if any(item.action.name == "PURGE_BLOCKED" for item in plan.items):
                    return ExecutionResult(ExecutionStatus.PERMANENT, "QUARANTINE_PLAN_BLOCKED", "lifecycle quarantine plan is blocked")
                ok, _ = self.domain.quarantine(plan, authorization_id=authorization.authorization_id)
            else:
                return ExecutionResult(ExecutionStatus.PERMANENT, "LIFECYCLE_JOB_TYPE", f"unsupported lifecycle job: {job.type.value}")
            return ExecutionResult(ExecutionStatus.SUCCESS if ok else ExecutionStatus.RETRYABLE, None if ok else "LIFECYCLE_FAILED", None if ok else "lifecycle action failed", 1.0)
        except OSError as exc:
            return ExecutionResult(ExecutionStatus.RETRYABLE, "LIFECYCLE_IO", str(exc), 1.0)


class VerificationJobExecutor:
    """Non-destructive checksum verification as a durable job."""

    def execute(self, job: Job, authorization: AuthorizationReceipt | None = None) -> ExecutionResult:
        if job.type is not JobType.VERIFY:
            return ExecutionResult(ExecutionStatus.PERMANENT, "WRONG_JOB_TYPE", "verification executor received another job type")
        target = job.source or job.path or job.destination
        if not target:
            return ExecutionResult(ExecutionStatus.PERMANENT, "VERIFY_INPUT", "verify job requires a target path")
        path = Path(target)
        try:
            if not path.is_file():
                return ExecutionResult(ExecutionStatus.PERMANENT, "VERIFY_MISSING", f"verification target is not a file: {path}")
            actual = sha256_file(path)
            if job.checksum and actual != job.checksum:
                return ExecutionResult(ExecutionStatus.PERMANENT, "VERIFY_MISMATCH", "checksum mismatch")
            return ExecutionResult(ExecutionStatus.SUCCESS)
        except OSError as exc:
            return ExecutionResult(ExecutionStatus.RETRYABLE, "VERIFY_IO", str(exc), 1.0)


class RcloneTransferBackend:
    """TransferManager backend using the existing protected RcloneAdapter.

    rclone's post-copy check is used as the verification boundary because a
    remote destination is not necessarily addressable as a local filesystem.
    """

    def __init__(self, adapter: RcloneAdapter | None = None) -> None:
        self.adapter = adapter or RcloneAdapter()

    def transfer(self, spec: TransferSpec, *, explicit_authorization: bool = False,
                 authorization: AuthorizationReceipt | None = None, progress_callback=None) -> TransferResult:
        receipt = authorization
        if not explicit_authorization and receipt is None:
            return TransferResult(False, 0, spec.source, spec.destination, error="explicit authorization required")
        result = self.adapter.copy(spec.source, spec.destination, authorization=receipt)
        if not result.success:
            return TransferResult(False, 0, spec.source, spec.destination, error=result.error or result.stderr)
        verified = self.adapter.check(spec.source, spec.destination, authorization=receipt)
        if not verified.success:
            return TransferResult(False, 0, spec.source, spec.destination, error=verified.error or verified.stderr)
        return TransferResult(True, 0, spec.source, spec.destination, verified=True)
