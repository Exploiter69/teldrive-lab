from pathlib import Path

from teldrive_lab.audit import open_audit
from teldrive_lab.job_lifecycle import AuditedJobStore, idempotency_key, reconcile
from teldrive_lab.jobs import JobState, JobType


def test_job_transitions_are_audited(tmp_path: Path) -> None:
    store = AuditedJobStore(tmp_path / "jobs.db", tmp_path / "audit.db")
    job = store.enqueue(JobType.INDEX, path="/tmp/example")
    claimed = store.claim("worker-1")
    assert claimed is not None
    completed = store.complete(job.job_id, "worker-1")
    assert completed.state is JobState.COMPLETED

    conn = open_audit(tmp_path / "audit.db")
    try:
        rows = conn.execute(
            "SELECT operation,result,job_id FROM events WHERE job_id=? ORDER BY id",
            (job.job_id,),
        ).fetchall()
    finally:
        conn.close()

    assert [(row[0], row[1]) for row in rows] == [
        ("JOB_ENQUEUE", "QUEUED"),
        ("JOB_CLAIM", "RUNNING"),
        ("JOB_COMPLETE", "COMPLETED"),
    ]
    assert all(row[2] == job.job_id for row in rows)


def test_retry_is_audited_with_error_code(tmp_path: Path) -> None:
    store = AuditedJobStore(tmp_path / "jobs.db", tmp_path / "audit.db")
    job = store.enqueue(JobType.DOWNLOAD, max_attempts=2)
    assert store.claim("worker") is not None
    retried = store.retry(
        job.job_id, "worker", error_code="TRANSIENT_NETWORK",
        error_message="temporary failure", delay_seconds=0,
    )
    assert retried.state is JobState.QUEUED

    conn = open_audit(tmp_path / "audit.db")
    try:
        row = conn.execute(
            "SELECT operation,error_code,result FROM events WHERE job_id=? ORDER BY id DESC LIMIT 1",
            (job.job_id,),
        ).fetchone()
    finally:
        conn.close()
    assert tuple(row) == ("JOB_RETRY", "TRANSIENT_NETWORK", "QUEUED")


def test_idempotency_key_is_stable_and_changes_with_identity() -> None:
    a = idempotency_key("UPLOAD", "/source/file", "sha256:abc")
    b = idempotency_key("UPLOAD", "/source/file", "sha256:abc")
    c = idempotency_key("UPLOAD", "/source/file", "sha256:def")
    assert a == b
    assert a != c


def test_reconciliation_refuses_ambiguous_existing_artifacts() -> None:
    assert reconcile(
        intended_checksum="abc", observed_checksum="abc", observed_exists=True
    ).safe_to_execute is False
    assert reconcile(
        intended_checksum="abc", observed_checksum="def", observed_exists=True
    ).safe_to_execute is False
    assert reconcile(
        intended_checksum="abc", observed_checksum=None, observed_exists=True
    ).safe_to_execute is False


def test_reconciliation_allows_absent_artifact() -> None:
    result = reconcile(
        intended_checksum="abc", observed_checksum=None, observed_exists=False
    )
    assert result.safe_to_execute is True
