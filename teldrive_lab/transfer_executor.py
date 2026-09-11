"""Job executor adapter for controlled local transfers."""

from __future__ import annotations

from pathlib import Path

from .jobs import Job, JobType
from .retry import RetryPolicy, classify_transfer_error, RetryClass
from .safety import AuthorizationReceipt, Operation
from .transfer import TransferManager, TransferSpec, sha256_file
from .worker import ExecutionResult, ExecutionStatus


class TransferJobExecutor:
    """Execute UPLOAD/DOWNLOAD jobs through the Phase 4 transfer manager."""

    SUPPORTED = frozenset({JobType.UPLOAD, JobType.DOWNLOAD})

    def __init__(self, manager: TransferManager | None = None,
                 retry_policy: RetryPolicy | None = None) -> None:
        self.manager = manager or TransferManager()
        self.retry_policy = retry_policy or RetryPolicy()

    def execute(
        self,
        job: Job,
        authorization: AuthorizationReceipt | None = None,
    ) -> ExecutionResult:
        if job.type not in self.SUPPORTED:
            return ExecutionResult(ExecutionStatus.PERMANENT, "UNSUPPORTED_JOB_TYPE",
                                   f"transfer executor cannot execute {job.type.value}")
        if not job.source or not job.destination:
            return ExecutionResult(ExecutionStatus.PERMANENT, "MISSING_TRANSFER_PATH",
                                   "transfer job requires source and destination")

        if authorization is not None and authorization.operation is not Operation.TRANSFER:
            return ExecutionResult(ExecutionStatus.UNSAFE, "AUTHORIZATION_SCOPE_MISMATCH",
                                   "transfer authorization does not match TRANSFER")

        result = self.manager.transfer(TransferSpec(job.source, job.destination), authorization=authorization)
        if result.success:
            return ExecutionResult(ExecutionStatus.SUCCESS)

        error = result.error or "transfer failed"
        if "protected production boundary" in error:
            return ExecutionResult(ExecutionStatus.UNSAFE, "PROTECTED_PRODUCTION", error)
        if "authorization" in error:
            return ExecutionResult(ExecutionStatus.UNSAFE, "UNAUTHORIZED", error)
        if "destination exists" in error or "source is not" in error:
            return ExecutionResult(ExecutionStatus.PERMANENT, "TRANSFER_INPUT", error)
        if "exceeds max_inflight_bytes" in error:
            return ExecutionResult(ExecutionStatus.PERMANENT, "TRANSFER_RESOURCE_LIMIT", error)

        code = "VERIFY_MISMATCH" if "checksum mismatch" in error else "TRANSFER_FAILED"
        category = classify_transfer_error(code)
        if category is RetryClass.INTEGRITY:
            delay = self.retry_policy.delay(max(1, job.attempts + 1), random_value=0.5)
            return ExecutionResult(ExecutionStatus.RETRYABLE, code, error, delay)
        if category in (RetryClass.TRANSIENT, RetryClass.RATE_LIMITED):
            delay = self.retry_policy.delay(max(1, job.attempts + 1), random_value=0.5)
            return ExecutionResult(ExecutionStatus.RETRYABLE, code, error, delay)
        return ExecutionResult(ExecutionStatus.PERMANENT, code, error)

    def reconcile(self, job: Job):
        from .job_lifecycle import reconcile
        if not job.destination:
            return type("RecoveryDecision", (), {"action": "FAIL", "reason": "recovery cannot identify transfer destination"})()
        destination = Path(job.destination)
        if not destination.is_file():
            return type("RecoveryDecision", (), {"action": "REQUEUE", "reason": "no completed destination observed"})()
        intended = job.checksum
        if intended is None and job.source and Path(job.source).is_file():
            intended = sha256_file(Path(job.source))
        if intended is None:
            return type("RecoveryDecision", (), {"action": "FAIL", "reason": "existing destination cannot be safely identified"})()
        observed = sha256_file(destination)
        result = reconcile(intended_checksum=intended, observed_checksum=observed, observed_exists=True)
        action = "COMPLETE" if result.reason == "matching checksum already observed" else ("REQUEUE" if result.safe_to_execute else "FAIL")
        return type("RecoveryDecision", (), {"action": action, "reason": result.reason})()
