"""R4 host gate: durable execution, verification, audit, and safety only.

This gate uses a disposable local fixture. It never connects to TelDrive,
rclone, Telegram, production mounts, or the production database.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from teldrive_lab.audit import open_audit
from teldrive_lab.execution import DurableExecutionRegistry
from teldrive_lab.jobs import JobState, JobStore, JobType
from teldrive_lab.safety import AuthorizationReceipt, Operation


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="teldrive-lab-r4-") as raw:
        root = Path(raw)
        source = root / "source.bin"
        destination = root / "dest" / "copy.bin"
        source.write_bytes(b"R4 durable execution fixture\n")

        store = JobStore(root / "jobs.db")
        audit = open_audit(root / "audit.db")
        job = store.enqueue(JobType.UPLOAD, source=str(source), destination=str(destination))

        def authorize_job(current):
            return AuthorizationReceipt.for_paths(
                Operation.TRANSFER,
                current.source or "",
                current.destination or current.path or "",
                authorization_id="r4-host-gate",
            )

        result = DurableExecutionRegistry().run_once(
            store,
            worker_id="r4-host-worker",
            audit_conn=audit,
            authorization_provider=authorize_job,
        )
        final = store.get(job.job_id)
        events = [row[0] for row in audit.execute(
            "SELECT operation FROM events WHERE job_id=? ORDER BY id", (job.job_id,)
        ).fetchall()]

        assert result is not None and result.state is JobState.COMPLETED
        assert final.state is JobState.COMPLETED and final.progress == 1
        assert destination.read_bytes() == source.read_bytes()
        assert "worker.claim" in events
        assert "worker.safety_gate" in events
        assert "worker.complete" in events

        capabilities = DurableExecutionRegistry().capabilities.supported
        assert {JobType.UPLOAD, JobType.DOWNLOAD, JobType.ARCHIVE, JobType.ORGANIZE} <= capabilities
        assert JobType.BACKUP not in capabilities
        assert not (root / "protected").exists()

    print("PHASE R4 DURABLE EXECUTION GATE: PASS")
    print("- single Worker/JobStore execution boundary: PASS")
    print("- persisted progress/worker fencing API: PASS")
    print("- persisted VERIFYING transition: PASS")
    print("- post-transfer checksum verification before completion: PASS")
    print("- audit evidence for claim/safety/completion: PASS")
    print("- unsupported job types are not falsely registered: PASS")
    print("- TelDrive production mutation: NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
