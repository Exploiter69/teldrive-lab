"""Controlled Phase 4 host gate; never touches TelDrive production data."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from teldrive_lab.concurrency import TransferLimiter, TransferLimits
from teldrive_lab.jobs import JobStore, JobType
from teldrive_lab.rclone import RcloneAdapter
from teldrive_lab.safety import AuthorizationReceipt, Operation
from teldrive_lab.transfer import TransferManager, TransferProgress, TransferSpec
from teldrive_lab.transfer_executor import TransferJobExecutor
from teldrive_lab.worker import Worker


class CountingExecutor:
    def __init__(self, delegate):
        self.delegate = delegate
        self.calls = 0

    def execute(self, job, authorization=None):
        self.calls += 1
        return self.delegate.execute(job, authorization)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="teldrive-lab-phase4-") as root:
        base = Path(root)
        source = base / "source.bin"
        destination = base / "nested" / "destination.bin"
        source.write_bytes(b"phase4-host-gate\n" * 512)
        store = JobStore(base / "jobs.db")
        manager = TransferManager(limiter=TransferLimiter(TransferLimits(max_workers=1, max_inflight_bytes=8 * 1024 * 1024)))

        progress: list[TransferProgress] = []
        receipt = AuthorizationReceipt.for_paths(Operation.TRANSFER, source, destination)
        result = manager.transfer(
            TransferSpec(str(source), str(destination)),
            authorization=receipt,
            progress_callback=progress.append,
        )
        assert result.success and result.verified
        assert destination.read_bytes() == source.read_bytes()
        assert progress and progress[-1].bytes_transferred == source.stat().st_size

        job = store.enqueue(JobType.UPLOAD, source=str(source), destination=str(base / "job-dest"))
        worker = Worker(
            store,
            TransferJobExecutor(manager),
            authorization_provider=lambda current: AuthorizationReceipt.for_paths(
                Operation.TRANSFER, current.source, current.destination
            ),
        )
        completed = worker.run_once()
        assert completed is not None and completed.state.value == "COMPLETED"

        blocked = store.enqueue(
            JobType.UPLOAD,
            source=str(source),
            destination="/home/thakuralok/TelegramRaw/phase4-host-gate.txt",
        )
        counting = CountingExecutor(TransferJobExecutor(manager))
        blocked_worker = Worker(
            store,
            counting,
            authorization_provider=lambda current: AuthorizationReceipt.for_paths(
                Operation.TRANSFER, current.source, current.destination
            ),
        )
        blocked_result = blocked_worker.run_once()
        assert blocked_result is not None and blocked_result.state.value == "FAILED"
        assert blocked_result.error_code == "UNSAFE_OPERATION"
        assert counting.calls == 0

        commands: list[list[str]] = []

        def runner(command):
            commands.append(list(command))
            return subprocess.CompletedProcess(command, 0, "dry-run", "")

        rclone = RcloneAdapter(runner=runner)
        dry_run = rclone.copy("source", "teldrive:phase4-host-gate", dry_run=True)
        assert dry_run.success and commands

    print("PHASE 4 HOST GATE: PASS")
    print("- isolated local transfer + checksum verification: PASS")
    print("- progress reporting: PASS")
    print("- durable UPLOAD worker execution: PASS")
    print("- protected production destination blocked before executor: PASS")
    print("- rclone adapter dry-run boundary: PASS")
    print("- no live TelDrive/rclone mutation performed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
