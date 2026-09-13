from pathlib import Path

import pytest

from teldrive_lab.audit import open_audit
from teldrive_lab.execution import DurableExecutionRegistry
from teldrive_lab.jobs import JobState, JobStore, JobType
from teldrive_lab.safety import AuthorizationReceipt, Operation


def _receipt(job):
    return AuthorizationReceipt.for_paths(
        Operation.TRANSFER,
        job.source or "",
        job.destination or "",
        authorization_id="r4-test",
    )


def test_job_store_persists_verifying_across_reopen(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.db")
    job = store.enqueue(JobType.UPLOAD, source=str(tmp_path / "src"), destination=str(tmp_path / "dst"))
    claimed = store.claim("worker")
    assert claimed is not None

    verifying = store.begin_verification(job.job_id, "worker")
    assert verifying.state is JobState.VERIFYING
    assert verifying.worker_id == "worker"

    reopened = JobStore(tmp_path / "jobs.db")
    assert reopened.get(job.job_id).state is JobState.VERIFYING

    completed = reopened.complete_verification(job.job_id, "worker")
    assert completed.state is JobState.COMPLETED
    assert completed.progress == 1


def test_progress_is_durable_and_worker_fenced(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.db")
    job = store.enqueue(JobType.UPLOAD, source="/tmp/source", destination="/tmp/destination")
    assert store.claim("worker-a") is not None
    updated = store.update_progress(job.job_id, "worker-a", 0.42)
    assert updated.progress == pytest.approx(0.42)
    assert JobStore(tmp_path / "jobs.db").get(job.job_id).progress == pytest.approx(0.42)
    with pytest.raises(ValueError):
        store.update_progress(job.job_id, "worker-b", 0.5)


def test_registry_routes_transfer_through_one_worker_boundary(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    destination = tmp_path / "archive" / "copy.bin"
    source.write_bytes(b"r4 durable execution\n")

    store = JobStore(tmp_path / "jobs.db")
    audit = open_audit(tmp_path / "audit.db")
    job = store.enqueue(JobType.UPLOAD, source=str(source), destination=str(destination))
    registry = DurableExecutionRegistry()

    result = registry.run_once(
        store,
        worker_id="r4-worker",
        audit_conn=audit,
        authorization_provider=_receipt,
    )

    assert result is not None
    assert result.state is JobState.COMPLETED
    assert result.progress == 1
    assert destination.read_bytes() == source.read_bytes()
    operations = [row[0] for row in audit.execute(
        "SELECT operation FROM events WHERE job_id=? ORDER BY id", (job.job_id,)
    ).fetchall()]
    assert "worker.claim" in operations
    assert "worker.safety_gate" in operations
    assert "worker.verifying" in operations
    assert "worker.complete" in operations


def test_registry_does_not_authorize_unsupported_job_types(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.db")
    job = store.enqueue(JobType.BACKUP, path=str(tmp_path / "backup"))
    registry = DurableExecutionRegistry()

    result = registry.run_once(store, worker_id="r4-worker")

    assert result is not None
    assert result.job_id == job.job_id
    assert result.state is JobState.FAILED
    assert result.error_code == "UNSUPPORTED_JOB_TYPE"
    assert not (tmp_path / "backup").exists()
