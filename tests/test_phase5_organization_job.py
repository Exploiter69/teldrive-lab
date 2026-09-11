from __future__ import annotations

from pathlib import Path

from teldrive_lab.jobs import Job, JobState, JobType
from teldrive_lab.organization import OrganizationJobExecutor
from teldrive_lab.safety import AuthorizationReceipt, Operation
from teldrive_lab.worker import ExecutionStatus


def job(source: Path, destination: Path) -> Job:
    return Job(
        job_id="phase5-job",
        type=JobType.ORGANIZE,
        state=JobState.RUNNING,
        priority="normal",
        attempts=0,
        max_attempts=3,
        retry_at=None,
        source=str(source),
        destination=str(destination),
        path=str(source),
        checksum=None,
        progress=0.0,
        error_code=None,
        error_message=None,
        worker_id="phase5-worker",
        lease_until=None,
        parent_job_id=None,
    )


def test_organize_job_executes_through_transfer_manager(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    destination = tmp_path / "organized" / "source.txt"
    source.write_bytes(b"phase5-job")
    current = job(source, destination)
    receipt = AuthorizationReceipt.for_paths(Operation.TRANSFER, source, destination, authorization_id="job-test")

    result = OrganizationJobExecutor().execute(current, receipt)

    assert result.status is ExecutionStatus.SUCCESS
    assert destination.read_bytes() == b"phase5-job"


def test_organize_job_rejects_unsafe_production_destination(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_bytes(b"phase5-job")
    destination = Path("/home/thakuralok/TelegramRaw/phase5-job.txt")
    current = job(source, destination)
    receipt = AuthorizationReceipt.for_paths(Operation.TRANSFER, source, destination, authorization_id="job-test")

    result = OrganizationJobExecutor().execute(current, receipt)

    assert result.status is ExecutionStatus.UNSAFE
    assert result.error_code == "PROTECTED_PRODUCTION"


def test_organize_job_requires_matching_authorization(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    destination = tmp_path / "organized" / "source.txt"
    source.write_bytes(b"phase5-job")
    current = job(source, destination)
    receipt = AuthorizationReceipt.for_paths(Operation.WRITE, source, destination, authorization_id="wrong")

    result = OrganizationJobExecutor().execute(current, receipt)

    assert result.status is ExecutionStatus.UNSAFE
    assert result.error_code == "AUTHORIZATION_SCOPE_MISMATCH"
