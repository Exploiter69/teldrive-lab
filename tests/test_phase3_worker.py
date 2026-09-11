from __future__ import annotations

from pathlib import Path

from teldrive_lab.audit import open_audit
from teldrive_lab.jobs import JobState, JobStore, JobType
from teldrive_lab.worker import ExecutionResult, ExecutionStatus, Worker


class FakeExecutor:
    def __init__(self, result: ExecutionResult):
        self.result = result
        self.calls = []

    def execute(self, job, authorization=None):
        self.calls.append(job)
        return self.result


def audit_results(conn):
    return [row[0] for row in conn.execute("SELECT result FROM events ORDER BY id")]


def test_worker_claims_and_completes_lab_job(tmp_path: Path):
    store = JobStore(tmp_path / "jobs.db")
    executor = FakeExecutor(ExecutionResult(ExecutionStatus.SUCCESS))
    audit = open_audit(tmp_path / "audit.db")
    job = store.enqueue(JobType.INDEX, path=str(tmp_path / "fixture"))

    result = Worker(store, executor, worker_id="w1", audit_conn=audit).run_once()

    assert result is not None
    assert result.state is JobState.COMPLETED
    assert len(executor.calls) == 1
    assert executor.calls[0].job_id == job.job_id
    assert audit_results(audit) == ["CLAIMED", "APPROVED", "COMPLETED"]


def test_retryable_failure_returns_to_queue_and_audits(tmp_path: Path):
    store = JobStore(tmp_path / "jobs.db")
    executor = FakeExecutor(ExecutionResult(
        ExecutionStatus.RETRYABLE, error_code="TEMP", error_message="temporary", delay_seconds=0,
    ))
    audit = open_audit(tmp_path / "audit.db")
    store.enqueue(JobType.INDEX, path=str(tmp_path / "fixture"), max_attempts=3)

    result = Worker(store, executor, worker_id="w1", audit_conn=audit).run_once()

    assert result.state is JobState.QUEUED
    assert result.attempts == 1
    assert audit_results(audit)[-1] == JobState.QUEUED.value


def test_permanent_failure_is_terminal(tmp_path: Path):
    store = JobStore(tmp_path / "jobs.db")
    executor = FakeExecutor(ExecutionResult(
        ExecutionStatus.PERMANENT, error_code="BAD_INPUT", error_message="permanent",
    ))
    job = store.enqueue(JobType.INDEX, path=str(tmp_path / "fixture"))

    result = Worker(store, executor, worker_id="w1").run_once()

    assert result.state is JobState.FAILED
    assert result.error_code == "BAD_INPUT"
    assert store.get(job.job_id).state is JobState.FAILED


def test_production_transfer_is_blocked_before_executor(tmp_path: Path):
    store = JobStore(tmp_path / "jobs.db")
    executor = FakeExecutor(ExecutionResult(ExecutionStatus.SUCCESS))
    audit = open_audit(tmp_path / "audit.db")
    job = store.enqueue(JobType.UPLOAD, source=str(tmp_path / "input"),
                         destination="~/TelegramRaw/blocked.bin")

    result = Worker(store, executor, worker_id="w1", audit_conn=audit).run_once()

    assert result.state is JobState.FAILED
    assert result.error_code == "UNSAFE_OPERATION"
    assert executor.calls == []
    assert "DENIED" in [row[0] for row in audit.execute("SELECT decision FROM events")]


def test_wrong_worker_cannot_complete_claimed_job(tmp_path: Path):
    store = JobStore(tmp_path / "jobs.db")
    job = store.enqueue(JobType.INDEX, path=str(tmp_path / "fixture"))
    claimed = store.claim("w1")

    assert claimed.job_id == job.job_id
    try:
        store.complete(job.job_id, "w2")
    except ValueError as exc:
        assert "worker" in str(exc)
    else:
        raise AssertionError("wrong worker completed the job")


def test_cancelled_execution_becomes_cancelled(tmp_path: Path):
    store = JobStore(tmp_path / "jobs.db")
    executor = FakeExecutor(ExecutionResult(ExecutionStatus.CANCELLED))
    job = store.enqueue(JobType.INDEX, path=str(tmp_path / "fixture"))

    result = Worker(store, executor, worker_id="w1").run_once()

    assert result.state is JobState.CANCELLED
    assert store.get(job.job_id).state is JobState.CANCELLED


def test_executor_exception_is_retryable(tmp_path: Path):
    class ExplodingExecutor:
        def __init__(self):
            self.calls = 0

        def execute(self, job, authorization=None):
            self.calls += 1
            raise RuntimeError("boom")

    store = JobStore(tmp_path / "jobs.db")
    executor = ExplodingExecutor()
    job = store.enqueue(JobType.INDEX, path=str(tmp_path / "fixture"), max_attempts=2)

    result = Worker(store, executor, worker_id="w1").run_once()

    assert executor.calls == 1
    assert result.state is JobState.QUEUED
    assert result.error_code == "EXECUTOR_EXCEPTION"
    assert result.attempts == 1
    assert store.get(job.job_id).worker_id is None


def test_worker_with_no_jobs_is_noop(tmp_path: Path):
    store = JobStore(tmp_path / "jobs.db")
    executor = FakeExecutor(ExecutionResult(ExecutionStatus.SUCCESS))

    result = Worker(store, executor, worker_id="w1").run_once()

    assert result is None
    assert executor.calls == []


def test_worker_never_self_authorizes_lab_mutation(tmp_path: Path):
    store = JobStore(tmp_path / "jobs.db")
    executor = FakeExecutor(ExecutionResult(ExecutionStatus.SUCCESS))
    store.enqueue(JobType.UPLOAD, source=str(tmp_path / "input"),
                  destination=str(tmp_path / "output"))

    result = Worker(store, executor, worker_id="w1").run_once()

    assert result.state is JobState.FAILED
    assert result.error_code == "UNSAFE_OPERATION"
    assert executor.calls == []
