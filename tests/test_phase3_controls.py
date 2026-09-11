from pathlib import Path

import pytest

from teldrive_lab.jobs import JobState, JobStore, JobType
from teldrive_lab.job_lifecycle import AuditedJobStore


def test_pause_resume_running_job_releases_lease(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.db")
    job = store.enqueue(JobType.INDEX)
    claimed = store.claim("worker-1", lease_seconds=60)
    assert claimed is not None

    paused = store.pause(job.job_id, "worker-1")
    assert paused.state is JobState.PAUSED
    assert paused.worker_id is None
    assert paused.lease_until is None

    resumed = store.resume(job.job_id)
    assert resumed.state is JobState.QUEUED
    assert resumed.worker_id is None

    reclaimed = store.claim("worker-2", lease_seconds=60)
    assert reclaimed is not None
    assert reclaimed.job_id == job.job_id
    assert reclaimed.worker_id == "worker-2"


def test_pause_rejects_wrong_worker(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.db")
    job = store.enqueue(JobType.INDEX)
    assert store.claim("worker-a") is not None
    with pytest.raises(ValueError):
        store.pause(job.job_id, "worker-b")


def test_parent_child_summary_is_durable(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.db")
    parent = store.enqueue(JobType.ARCHIVE)
    first = store.enqueue(JobType.INDEX, parent_job_id=parent.job_id)
    second = store.enqueue(JobType.VERIFY, parent_job_id=parent.job_id)

    children = store.children(parent.job_id)
    assert [child.job_id for child in children] == [first.job_id, second.job_id]
    summary = store.child_summary(parent.job_id)
    assert summary.total == 2
    assert summary.queued == 2
    assert not summary.terminal

    assert store.claim("worker") is not None
    store.complete(first.job_id, "worker")
    summary = store.child_summary(parent.job_id)
    assert summary.completed == 1
    assert summary.queued == 1

    assert store.claim("worker") is not None
    store.complete(second.job_id, "worker")
    summary = JobStore(tmp_path / "jobs.db").child_summary(parent.job_id)
    assert summary.successful


def test_child_cannot_be_added_to_terminal_parent(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.db")
    parent = store.enqueue(JobType.ARCHIVE)
    assert store.claim("worker") is not None
    store.complete(parent.job_id, "worker")
    with pytest.raises(ValueError):
        store.enqueue(JobType.INDEX, parent_job_id=parent.job_id)


def test_audited_pause_and_resume_are_persisted(tmp_path: Path) -> None:
    audited = AuditedJobStore(tmp_path / "jobs.db", tmp_path / "audit.db")
    job = audited.enqueue(JobType.INDEX)
    assert audited.claim("worker") is not None
    paused = audited.pause(job.job_id, "worker")
    assert paused.state is JobState.PAUSED
    resumed = audited.resume(job.job_id)
    assert resumed.state is JobState.QUEUED

    import sqlite3
    with sqlite3.connect(tmp_path / "audit.db") as conn:
        operations = [row[0] for row in conn.execute("SELECT operation FROM events ORDER BY id")]
    assert operations == ["JOB_ENQUEUE", "JOB_CLAIM", "JOB_PAUSE", "JOB_RESUME"]
