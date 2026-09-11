from pathlib import Path

from teldrive_lab.jobs import JobState, JobStore, JobType
from teldrive_lab.worker import ExecutionResult, ExecutionStatus, Worker


class PausingExecutor:
    def __init__(self, store: JobStore) -> None:
        self.store = store

    def execute(self, job):
        self.store.pause(job.job_id, "worker")
        return ExecutionResult(ExecutionStatus.SUCCESS)


def test_worker_does_not_overwrite_pause_with_completion(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.db")
    job = store.enqueue(JobType.INDEX, path=str(tmp_path / "fixture"))
    worker = Worker(store, PausingExecutor(store), worker_id="worker")

    result = worker.run_once()
    assert result is not None
    assert result.state is JobState.PAUSED
    assert store.get(job.job_id).state is JobState.PAUSED
