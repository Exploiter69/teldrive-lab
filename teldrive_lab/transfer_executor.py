"""Job executor adapter for controlled local transfers.

The executor owns no authorization policy. The worker supplies the scoped
receipt that was issued by the higher-level authorization boundary.
"""

from __future__ import annotations

from .jobs import Job, JobType
from .safety import AuthorizationReceipt, Operation
from .transfer import TransferManager, TransferSpec
from .worker import ExecutionResult, ExecutionStatus


class TransferJobExecutor:
    """Execute UPLOAD/DOWNLOAD jobs through the Phase 4 transfer manager."""

    SUPPORTED = frozenset({JobType.UPLOAD, JobType.DOWNLOAD})

    def __init__(self, manager: TransferManager | None = None) -> None:
        self.manager = manager or TransferManager()

    def execute(
        self,
        job: Job,
        authorization: AuthorizationReceipt | None = None,
    ) -> ExecutionResult:
        if job.type not in self.SUPPORTED:
            return ExecutionResult(
                ExecutionStatus.PERMANENT,
                error_code="UNSUPPORTED_JOB_TYPE",
                error_message=f"transfer executor cannot execute {job.type.value}",
            )
        if not job.source or not job.destination:
            return ExecutionResult(
                ExecutionStatus.PERMANENT,
                error_code="MISSING_TRANSFER_PATH",
                error_message="transfer job requires source and destination",
            )

        operation = Operation.TRANSFER
        if authorization is not None and authorization.operation is not operation:
            return ExecutionResult(
                ExecutionStatus.UNSAFE,
                error_code="AUTHORIZATION_SCOPE_MISMATCH",
                error_message="transfer authorization does not match TRANSFER",
            )

        result = self.manager.transfer(
            TransferSpec(job.source, job.destination),
            authorization=authorization,
        )
        if result.success:
            return ExecutionResult(ExecutionStatus.SUCCESS)

        error = result.error or "transfer failed"
        if "protected production boundary" in error:
            return ExecutionResult(ExecutionStatus.UNSAFE, "PROTECTED_PRODUCTION", error)
        if "authorization" in error:
            return ExecutionResult(ExecutionStatus.UNSAFE, "UNAUTHORIZED", error)
        if "destination exists" in error or "source is not" in error:
            return ExecutionResult(ExecutionStatus.PERMANENT, "TRANSFER_INPUT", error)
        if "checksum mismatch" in error:
            return ExecutionResult(ExecutionStatus.RETRYABLE, "VERIFY_MISMATCH", error)
        return ExecutionResult(ExecutionStatus.RETRYABLE, "TRANSFER_FAILED", error)
