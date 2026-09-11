from pathlib import Path

from teldrive_lab.jobs import JobState, JobStore, JobType
from teldrive_lab.safety import AuthorizationReceipt, Operation
from teldrive_lab.transfer_executor import TransferJobExecutor
from teldrive_lab.worker import ExecutionStatus, Worker


def test_authorized_transfer_job_completes_and_verifies(tmp_path: Path):
    source = tmp_path / "source.txt"
    destination = tmp_path / "nested" / "copy.txt"
    source.write_text("durable transfer")

    store = JobStore(tmp_path / "jobs.db")
    job = store.enqueue(
        JobType.UPLOAD,
        source=str(source),
        destination=str(destination),
    )
    receipt = AuthorizationReceipt.for_paths(
        Operation.TRANSFER,
        str(source),
        str(destination),
        authorization_id="test-approved-transfer",
    )

    result = Worker(
        store,
        TransferJobExecutor(),
        worker_id="transfer-worker",
        authorization_provider=lambda _: receipt,
    ).run_once()

    assert result.state is JobState.COMPLETED
    assert destination.read_text() == "durable transfer"


def test_transfer_job_without_authorization_never_executes(tmp_path: Path):
    source = tmp_path / "source.txt"
    destination = tmp_path / "copy.txt"
    source.write_text("must remain local")

    store = JobStore(tmp_path / "jobs.db")
    store.enqueue(JobType.UPLOAD, source=str(source), destination=str(destination))

    result = Worker(store, TransferJobExecutor(), worker_id="transfer-worker").run_once()

    assert result.state is JobState.FAILED
    assert result.error_code == "UNSAFE_OPERATION"
    assert not destination.exists()


def test_authorization_scope_mismatch_is_blocked(tmp_path: Path):
    source = tmp_path / "source.txt"
    destination = tmp_path / "copy.txt"
    other = tmp_path / "other.txt"
    source.write_text("scope")

    store = JobStore(tmp_path / "jobs.db")
    store.enqueue(JobType.UPLOAD, source=str(source), destination=str(destination))
    receipt = AuthorizationReceipt.for_paths(
        Operation.TRANSFER, str(source), str(other), authorization_id="wrong-scope"
    )

    result = Worker(
        store,
        TransferJobExecutor(),
        worker_id="transfer-worker",
        authorization_provider=lambda _: receipt,
    ).run_once()

    assert result.state is JobState.FAILED
    assert result.error_code == "UNSAFE_OPERATION"
    assert not destination.exists()


def test_protected_transfer_is_denied_even_with_receipt(tmp_path: Path):
    source = tmp_path / "source.txt"
    source.write_text("never production")
    destination = "/home/thakuralok/TelegramRaw/phase4-worker-test.txt"

    store = JobStore(tmp_path / "jobs.db")
    store.enqueue(JobType.UPLOAD, source=str(source), destination=destination)
    receipt = AuthorizationReceipt.for_paths(
        Operation.TRANSFER, str(source), destination, authorization_id="attempt-production"
    )

    result = Worker(
        store,
        TransferJobExecutor(),
        worker_id="transfer-worker",
        authorization_provider=lambda _: receipt,
    ).run_once()

    assert result.state is JobState.FAILED
    assert result.error_code == "UNSAFE_OPERATION"
    assert not Path(destination).exists()


def test_executor_classifies_missing_source_as_permanent(tmp_path: Path):
    store = JobStore(tmp_path / "jobs.db")
    source = tmp_path / "missing.txt"
    destination = tmp_path / "copy.txt"
    job = store.enqueue(JobType.UPLOAD, source=str(source), destination=str(destination))
    receipt = AuthorizationReceipt.for_paths(Operation.TRANSFER, str(source), str(destination))

    claimed = store.claim("worker")
    result = TransferJobExecutor().execute(claimed, receipt)

    assert result.status is ExecutionStatus.PERMANENT
    assert result.error_code == "TRANSFER_INPUT"
    assert job.job_id == claimed.job_id
