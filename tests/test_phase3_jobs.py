from pathlib import Path

import pytest

from teldrive_lab.jobs import JobState, JobStore, JobType


def test_enqueue_claim_complete_survives_reopen(tmp_path: Path) -> None:
    db = tmp_path / "jobs.db"
    store = JobStore(db)
    created = store.enqueue(JobType.INDEX, path="/safe/path")
    assert created.state is JobState.QUEUED

    claimed = store.claim("worker-1", lease_seconds=60)
    assert claimed is not None
    assert claimed.state is JobState.RUNNING
    assert claimed.worker_id == "worker-1"

    reopened = JobStore(db)
    completed = reopened.complete(created.job_id, "worker-1")
    assert completed.state is JobState.COMPLETED
    assert completed.progress == 1


def test_expired_lease_is_requeued(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.db")
    job = store.enqueue(JobType.VERIFY)
    claimed = store.claim("dead-worker", lease_seconds=0.01)
    assert claimed is not None

    import time
    time.sleep(0.03)
    assert store.recover_expired_leases() == 1
    recovered = store.get(job.job_id)
    assert recovered.state is JobState.QUEUED
    assert recovered.worker_id is None


def test_retry_is_bounded_and_eventually_fails(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.db")
    job = store.enqueue(JobType.DOWNLOAD, max_attempts=2)

    first = store.claim("worker")
    assert first is not None
    queued = store.retry(job.job_id, "worker", error_code="TRANSIENT", error_message="network", delay_seconds=0)
    assert queued.state is JobState.QUEUED
    assert queued.attempts == 1

    second = store.claim("worker")
    assert second is not None
    failed = store.retry(job.job_id, "worker", error_code="TRANSIENT", error_message="network", delay_seconds=0)
    assert failed.state is JobState.FAILED
    assert failed.attempts == 2


def test_cancellation_is_persistent(tmp_path: Path) -> None:
    db = tmp_path / "jobs.db"
    store = JobStore(db)
    job = store.enqueue(JobType.ARCHIVE)
    cancelled = store.cancel(job.job_id)
    assert cancelled.state is JobState.CANCELLED
    assert JobStore(db).get(job.job_id).state is JobState.CANCELLED


def test_invalid_completion_cannot_cross_worker_boundary(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.db")
    job = store.enqueue(JobType.INDEX)
    assert store.claim("worker-a") is not None
    with pytest.raises(ValueError):
        store.complete(job.job_id, "worker-b")
