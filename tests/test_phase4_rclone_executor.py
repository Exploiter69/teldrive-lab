from __future__ import annotations

import subprocess

from teldrive_lab.jobs import JobStore, JobType
from teldrive_lab.rclone import RcloneAdapter
from teldrive_lab.retry import RetryPolicy
from teldrive_lab.safety import AuthorizationReceipt, Operation
from teldrive_lab.transfer_executor import TransferJobExecutor
from teldrive_lab.worker import ExecutionStatus


def test_rclone_failure_is_reported_without_shell_execution():
    calls = []

    def runner(command):
        calls.append(command)
        return subprocess.CompletedProcess(command, 1, "", "network reset")

    adapter = RcloneAdapter(runner=runner)
    receipt = AuthorizationReceipt.for_paths(Operation.TRANSFER, "source", "remote:path")
    result = adapter.copy("source", "remote:path", authorization=receipt)
    assert result.success is False
    assert result.returncode == 1
    assert len(calls) == 1
    assert all(not isinstance(part, bytes) for part in calls[0])


def test_transfer_executor_returns_bounded_retry_delay(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.write_text("payload")
    destination.write_text("existing")

    store = JobStore(tmp_path / "jobs.db")
    job = store.enqueue(JobType.UPLOAD, source=str(source), destination=str(destination), max_attempts=3)
    executor = TransferJobExecutor(retry_policy=RetryPolicy(base_delay=2, max_delay=8, jitter=0))
    result = executor.execute(job, AuthorizationReceipt.for_paths(Operation.TRANSFER, source, destination))

    assert result.status is ExecutionStatus.PERMANENT
    assert result.error_code == "TRANSFER_INPUT"


def test_transfer_executor_reports_checksum_failure_as_retryable(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.write_text("payload")

    class BadManager:
        def transfer(self, *args, **kwargs):
            from teldrive_lab.transfer import TransferResult
            return TransferResult(False, 7, str(source), str(destination), error="post-transfer checksum mismatch")

    store = JobStore(tmp_path / "jobs.db")
    job = store.enqueue(JobType.UPLOAD, source=str(source), destination=str(destination), max_attempts=3)
    executor = TransferJobExecutor(manager=BadManager(), retry_policy=RetryPolicy(base_delay=2, max_delay=8, jitter=0))
    result = executor.execute(job, AuthorizationReceipt.for_paths(Operation.TRANSFER, source, destination))

    assert result.status is ExecutionStatus.RETRYABLE
    assert result.error_code == "VERIFY_MISMATCH"
    assert result.delay_seconds == 2
