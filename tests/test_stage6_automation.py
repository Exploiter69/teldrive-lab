import time
from pathlib import Path

from teldrive_lab.automation import (
    approval_required,
    approval_status,
    create_schedule,
    degraded_action,
    dependency_ready,
    due_schedules,
    ingest_event,
    init_automation_db,
    local_notification,
    request_approval,
    verification_plan,
    verification_required,
    webhook_payload,
    decide_approval,
)
from teldrive_lab.jobs import JobState, JobStore, JobType


def test_schedule_is_durable_and_due(tmp_path: Path):
    db = tmp_path / "automation.db"
    create_schedule(db, JobType.BACKUP, interval_seconds=60, start_at=100.0)
    assert due_schedules(db, now=99) == []
    assert due_schedules(db, now=100)[0].job_type is JobType.BACKUP


def test_due_schedule_materializes_durable_job(tmp_path: Path):
    db = tmp_path / "automation.db"
    jobs = JobStore(tmp_path / "jobs.db")
    create_schedule(db, JobType.VERIFY, interval_seconds=60, start_at=100.0)
    from teldrive_lab.automation import materialize_due_schedule
    job = materialize_due_schedule(db, due_schedules(db, now=100)[0].schedule_id, jobs, now=100)
    assert job.state is JobState.QUEUED
    assert due_schedules(db, now=100) == []


def test_event_ingestion_is_durable(tmp_path: Path):
    db = tmp_path / "automation.db"
    eid = ingest_event(db, "object.added", {"object_id": "x"}, event_id="e1")
    assert eid == "e1"
    assert db.exists()


def test_dependencies_require_completed_parent(tmp_path: Path):
    jobs = JobStore(tmp_path / "jobs.db")
    parent = jobs.enqueue(JobType.UPLOAD)
    child = jobs.enqueue(JobType.VERIFY, parent_job_id=parent.job_id)
    assert dependency_ready(jobs, child) is False


def test_mutations_require_verification():
    assert verification_required(JobType.UPLOAD) is True
    assert verification_required(JobType.INDEX) is False
    assert verification_plan(type("J", (), {"job_id": "x", "type": JobType.UPLOAD})())["required"] is True


def test_high_risk_operations_require_approval():
    assert approval_required(JobType.CLEANUP) is True
    assert approval_required(JobType.BACKUP) is False


def test_approval_is_explicit_and_durable(tmp_path: Path):
    db = tmp_path / "automation.db"
    aid = request_approval(db, "CLEANUP", job_id="j1")
    assert approval_status(db, aid) == "PENDING"
    decide_approval(db, aid, approved=True, reason="operator confirmed")
    assert approval_status(db, aid) == "APPROVED"


def test_webhook_is_versioned_and_non_authoritative():
    assert webhook_payload("job.completed", job_id="j1", result="ok")["version"] == 1


def test_local_notification_uses_local_spool(tmp_path: Path):
    path = tmp_path / "notifications.ndjson"
    local_notification(path, "Job complete", "Verified")
    assert path.read_text(encoding="utf-8").count("Job complete") == 1


def test_degraded_provider_pauses():
    assert degraded_action("DEGRADED") == "PAUSE_AND_RETRY"
    assert degraded_action("HEALTHY") == "CONTINUE"
