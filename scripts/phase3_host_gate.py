"""Controlled Phase 3 host gate using only temporary Lab fixtures.

This gate never writes to TelDrive production paths. It exercises the durable
JobStore, Worker safety gate, executor boundary, and audit trail on the host.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from teldrive_lab.audit import open_audit
from teldrive_lab.jobs import JobState, JobStore, JobType
from teldrive_lab.worker import ExecutionResult, ExecutionStatus, Worker


class FixtureExecutor:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def execute(self, job):
        self.calls.append(job.job_id)
        if job.type is JobType.INDEX:
            assert job.path is not None
            assert Path(job.path).exists()
            return ExecutionResult(ExecutionStatus.SUCCESS)
        return ExecutionResult(ExecutionStatus.SUCCESS)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="teldrive-lab-phase3-") as raw:
        root = Path(raw)
        fixture = root / "fixture.txt"
        fixture.write_text("phase3 host gate\n", encoding="utf-8")
        jobs_db = root / "jobs.db"
        audit_db = root / "audit.db"

        store = JobStore(jobs_db)
        executor = FixtureExecutor()
        with open_audit(audit_db) as audit:
            worker = Worker(store, executor, worker_id="phase3-gate", audit_conn=audit)

            safe = store.enqueue(JobType.INDEX, path=str(fixture))
            result = worker.run_once()
            assert result is not None and result.job_id == safe.job_id
            assert result.state is JobState.COMPLETED
            assert executor.calls == [safe.job_id]

            protected = store.enqueue(
                JobType.ARCHIVE,
                source="~/TelegramRaw/phase3-gate-must-not-touch",
            )
            blocked = worker.run_once()
            assert blocked is not None and blocked.job_id == protected.job_id
            assert blocked.state is JobState.FAILED
            assert blocked.error_code == "UNSAFE_OPERATION"
            assert executor.calls == [safe.job_id]

        with sqlite3.connect(audit_db) as conn:
            count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            blocked_events = conn.execute(
                "SELECT COUNT(*) FROM events WHERE operation='worker.safety_gate' AND decision='DENIED'"
            ).fetchone()[0]

        assert count >= 7
        assert blocked_events == 1
        print("PHASE3 CONTROLLED HOST GATE: PASS")
        print(f"completed_job={safe.job_id}")
        print(f"blocked_job={protected.job_id}")
        print(f"audit_events={count}")


if __name__ == "__main__":
    main()
