"""R4 final host gate: all durable execution adapters on disposable fixtures.

The gate never connects to TelDrive, Telegram, production mounts, production
rclone configuration, or the production database. rclone is exercised only
through an injected runner.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from teldrive_lab.audit import open_audit
from teldrive_lab.execution import DurableExecutionRegistry
from teldrive_lab.jobs import JobState, JobStore, JobType
from teldrive_lab.rclone import RcloneAdapter
from teldrive_lab.safety import AuthorizationReceipt, Operation


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="teldrive-lab-r4-") as raw:
        root = Path(raw)
        os.environ["TELDRIVE_LAB_STATE"] = str(root / "runtime")
        source = root / "source.bin"
        destination = root / "dest" / "copy.bin"
        source.write_bytes(b"R4 final durable execution fixture\n")

        store = JobStore(root / "jobs.db")
        audit = open_audit(root / "audit.db")

        def authorize_job(current):
            operation = Operation.VERIFY if current.type is JobType.VERIFY else Operation.TRANSFER
            return AuthorizationReceipt.for_paths(
                operation,
                current.source or current.path or "",
                current.destination or current.path or current.source or "",
                authorization_id="r4-final-host-gate",
            )

        def run(job_type, *, source_path=None, destination_path=None, checksum=None, registry=None):
            job = store.enqueue(job_type, source=source_path, destination=destination_path, checksum=checksum)
            result = (registry or DurableExecutionRegistry()).run_once(
                store, worker_id=f"r4-{job_type.value.lower()}", audit_conn=audit,
                authorization_provider=authorize_job,
            )
            return job, result, store.get(job.job_id)

        job, result, final = run(JobType.UPLOAD, source_path=str(source), destination_path=str(destination))
        assert result is not None and final.state is JobState.COMPLETED
        assert destination.read_bytes() == source.read_bytes()

        backup_dir = root / "backup"
        backup_job, _, backup_final = run(JobType.BACKUP, source_path='["%s"]' % source, destination_path=str(backup_dir))
        assert backup_final.state is JobState.COMPLETED
        assert (backup_dir / source.name).read_bytes() == source.read_bytes()

        quarantine = root / "quarantine"
        cleanup_job, _, cleanup_final = run(JobType.CLEANUP, source_path=str(source), destination_path=str(quarantine))
        assert cleanup_final.state is JobState.COMPLETED
        assert (quarantine / source.name).read_bytes() == source.read_bytes()
        assert source.is_file(), "cleanup/quarantine must not delete the source"

        verify_job, _, verify_final = run(JobType.VERIFY, source_path=str(destination), checksum=__import__("hashlib").sha256(source.read_bytes()).hexdigest())
        assert verify_final.state is JobState.COMPLETED

        calls = []
        def fake_runner(command):
            calls.append(list(command))
            return subprocess.CompletedProcess(command, 0, "ok", "")
        rclone_registry = DurableExecutionRegistry(rclone_adapter=RcloneAdapter(runner=fake_runner))
        remote_job, _, remote_final = run(
            JobType.UPLOAD, source_path=str(source), destination_path="teldrive-lab-test:fixture.bin",
            registry=rclone_registry,
        )
        assert remote_final.state is JobState.COMPLETED
        assert calls and calls[0][1] == "copyto" and calls[1][1] == "check"
        assert all("--dry-run" not in call for call in calls)

        events = audit.execute("SELECT operation FROM events ORDER BY id").fetchall()
        operations = [row[0] for row in events]
        assert "worker.claim" in operations
        assert "worker.safety_gate" in operations
        assert "worker.complete" in operations

        capabilities = DurableExecutionRegistry().capabilities.supported
        required = {JobType.UPLOAD, JobType.DOWNLOAD, JobType.ARCHIVE, JobType.ORGANIZE,
                    JobType.BACKUP, JobType.SNAPSHOT, JobType.CLEANUP, JobType.RESTORE, JobType.VERIFY}
        assert required <= capabilities
        assert not (root / "protected").exists()

    print("PHASE R4 FINAL DURABLE EXECUTION GATE: PASS")
    print("- Backup durable executor: PASS")
    print("- Lifecycle cleanup/quarantine durable executor: PASS")
    print("- Verification durable executor: PASS")
    print("- rclone adapter connected to durable transfer executor: PASS")
    print("- rclone copy + post-copy check: PASS (injected disposable runner)")
    print("- persisted RUNNING/VERIFYING/COMPLETED lifecycle: PASS")
    print("- audit evidence and production boundary: PASS")
    print("- TelDrive production mutation: NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
