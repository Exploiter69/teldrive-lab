from __future__ import annotations

from pathlib import Path

from teldrive_lab.archive import ArchiveJobExecutor
from teldrive_lab.jobs import Job, JobState, JobType
from teldrive_lab.safety import AuthorizationReceipt, Operation
from teldrive_lab.worker import ExecutionStatus


def make_job(
    source: Path | None,
    destination: Path | None,
    *,
    job_type: JobType = JobType.ARCHIVE,
) -> Job:
    return Job(
        job_id="phase6-job",
        type=job_type,
        state=JobState.RUNNING,
        priority="NORMAL",
        attempts=0,
        max_attempts=3,
        retry_at=None,
        source=str(source) if source else None,
        destination=str(destination) if destination else None,
        path=str(source) if source else None,
        checksum=None,
        progress=0.0,
        error_code=None,
        error_message=None,
        worker_id="phase6-worker",
        lease_until=None,
        parent_job_id=None,
    )


def test_archive_job_executes_through_transfer_manager(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    destination = tmp_path / "archive" / "source.txt"
    source.write_bytes(b"phase6-job")

    current = make_job(source, destination)
    receipt = AuthorizationReceipt.for_paths(
        Operation.TRANSFER,
        source,
        destination,
        authorization_id="phase6-job-test",
    )

    result = ArchiveJobExecutor().execute(current, receipt)

    assert result.status is ExecutionStatus.SUCCESS
    assert destination.read_bytes() == b"phase6-job"


def test_archive_job_rejects_unsupported_job_type(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    destination = tmp_path / "archive" / "source.txt"
    source.write_bytes(b"phase6-job")

    current = make_job(source, destination, job_type=JobType.ORGANIZE)

    result = ArchiveJobExecutor().execute(current)

    assert result.status is ExecutionStatus.PERMANENT
    assert result.error_code == "UNSUPPORTED_JOB_TYPE"


def test_archive_job_requires_source_and_destination(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_bytes(b"phase6-job")

    missing_source = ArchiveJobExecutor().execute(
        make_job(None, tmp_path / "archive" / "source.txt")
    )
    missing_destination = ArchiveJobExecutor().execute(
        make_job(source, None)
    )

    assert missing_source.status is ExecutionStatus.PERMANENT
    assert missing_source.error_code == "MISSING_ARCHIVE_PATH"
    assert missing_destination.status is ExecutionStatus.PERMANENT
    assert missing_destination.error_code == "MISSING_ARCHIVE_PATH"


def test_archive_job_requires_transfer_authorization(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    destination = tmp_path / "archive" / "source.txt"
    source.write_bytes(b"phase6-job")

    current = make_job(source, destination)
    receipt = AuthorizationReceipt.for_paths(
        Operation.WRITE,
        source,
        destination,
        authorization_id="wrong-operation",
    )

    result = ArchiveJobExecutor().execute(current, receipt)

    assert result.status is ExecutionStatus.UNSAFE
    assert result.error_code == "AUTHORIZATION_SCOPE_MISMATCH"
    assert not destination.exists()


def test_archive_job_blocks_protected_production_destination(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_bytes(b"phase6-job")
    destination = Path("/home/thakuralok/TelegramRaw/phase6-job.txt")

    current = make_job(source, destination)
    receipt = AuthorizationReceipt.for_paths(
        Operation.TRANSFER,
        source,
        destination,
        authorization_id="protected-destination",
    )

    result = ArchiveJobExecutor().execute(current, receipt)

    assert result.status is ExecutionStatus.UNSAFE
    assert result.error_code == "PROTECTED_PRODUCTION"
    assert source.read_bytes() == b"phase6-job"


def test_archive_job_rejects_existing_destination(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    destination = tmp_path / "archive" / "source.txt"
    source.write_bytes(b"phase6-job")
    destination.parent.mkdir()
    destination.write_bytes(b"existing")

    current = make_job(source, destination)
    receipt = AuthorizationReceipt.for_paths(
        Operation.TRANSFER,
        source,
        destination,
        authorization_id="existing-destination",
    )

    result = ArchiveJobExecutor().execute(current, receipt)

    assert result.status is ExecutionStatus.PERMANENT
    assert result.error_code == "ARCHIVE_INPUT"
    assert destination.read_bytes() == b"existing"
