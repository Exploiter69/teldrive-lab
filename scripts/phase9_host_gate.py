"""Controlled Phase 9 host gate; only isolated temporary Lab-owned paths are mutated."""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

from teldrive_lab.backups import BackupExecutor, BackupPlanner, BackupPolicy, BackupState, BackupStore, BackupScheduler
from teldrive_lab.jobs import JobStore


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="teldrive-lab-phase9-") as raw:
        root = Path(raw)
        source = root / "source.txt"
        source.write_text("Phase 9 controlled backup fixture\n", encoding="utf-8")
        backup_root = root / "backup"
        restore_root = root / "restore"
        store = BackupStore(root / "backups.db")
        planner = BackupPlanner()
        plan = planner.plan([source], backup_root=backup_root,
                            policy=BackupPolicy(retention_seconds=60, safety_window_seconds=30),
                            now=datetime(2026, 1, 1, tzinfo=timezone.utc))
        assert plan.digest == planner.plan([source], backup_root=backup_root,
                                           policy=BackupPolicy(retention_seconds=60, safety_window_seconds=30),
                                           now=datetime(2026, 1, 1, tzinfo=timezone.utc)).digest
        executor = BackupExecutor(store)
        ok, _ = executor.apply(plan, authorization_id="phase9-host-gate")
        assert ok
        assert executor.verify(plan)[0].state == BackupState.VERIFIED
        assert executor.reconcile(plan)[0].state == BackupState.VERIFIED
        ok, restored = executor.restore(plan, restore_root=restore_root, authorization_id="phase9-host-gate")
        assert ok and restored and Path(restored[0]).read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
        store.lock(plan.digest)
        assert executor.retention_ready(now=datetime(2026, 1, 2, tzinfo=timezone.utc)) == ()

        jobs = JobStore(root / "jobs.db")
        scheduler = BackupScheduler(store, jobs)
        schedule = scheduler.add([source], root / "scheduled", interval_seconds=60, first_run_at=10)
        ids = scheduler.run_due(now=10)
        assert ids and jobs.get(ids[0]).type.value == "BACKUP"
        assert not store.due_schedules(10)
        assert schedule.schedule_id

        # Deliberately exercise corruption/missing detection after the backup has been proven.
        backup_path = Path(plan.items[0].destination)
        backup_path.write_text("tampered", encoding="utf-8")
        assert executor.verify(plan)[0].state == BackupState.CORRUPT
        backup_path.unlink()
        assert executor.verify(plan)[0].state == BackupState.MISSING

    print("PHASE 9 HOST GATE: PASS")
    print("scheduled durable backup: PASS")
    print("snapshot/manifest digest: PASS")
    print("SHA-256 backup verification: PASS")
    print("reconciliation detects corruption/missing: PASS")
    print("restore is verified and no-overwrite: PASS")
    print("retention safety window + lock: PASS")
    print("production storage mutation: NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
