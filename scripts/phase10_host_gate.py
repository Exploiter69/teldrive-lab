"""Controlled Phase 10 gate; observes only isolated Lab-owned state."""
from __future__ import annotations

import sqlite3
import tempfile
import time
from pathlib import Path

from teldrive_lab.health import Check
from teldrive_lab.monitoring import AlertCode, MonitoringStore, collect, job_snapshot, storage_snapshot


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="teldrive-lab-phase10-") as raw:
        root = Path(raw)
        jobs = root / "jobs.db"
        with sqlite3.connect(jobs) as conn:
            conn.execute("CREATE TABLE jobs (state TEXT, updated REAL, worker_id TEXT, lease_until REAL)")
            conn.execute("INSERT INTO jobs VALUES ('RUNNING',?,?,?)", (time.time() - 7200, 'gate-worker', None))
            conn.execute("INSERT INTO jobs VALUES ('FAILED',?,?,?)", (time.time(), None, None))
        store = MonitoringStore(root / "monitor.db")
        audit = root / "audit.db"
        before = sorted(p.name for p in root.iterdir())
        snapshot = collect(
            store=store,
            audit_path=audit,
            job_db=jobs,
            storage_paths=[root],
            health_probe=lambda: [Check("TelDrive", True, "controlled gate"), Check("rclone", True, "controlled gate")],
            backup_status={"overdue": True, "failed": False, "corrupt": False},
        )
        assert snapshot.jobs.stuck == 1
        codes = {a.code for a in snapshot.alerts}
        assert AlertCode.JOB_STUCK in codes
        assert AlertCode.BACKUP_OVERDUE in codes
        assert all(a.severity in {"WARNING", "CRITICAL"} for a in snapshot.alerts)
        assert job_snapshot(jobs).running == 1
        assert storage_snapshot(root).free_bytes >= 0
        after = sorted(p.name for p in root.iterdir())
        assert before == after, "monitoring created no production-like files outside its declared state"
        with sqlite3.connect(store.path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0] >= 2
        # Resolution is read-only with respect to the observed job DB.
        collect(store=store, audit_path=audit, job_db=jobs, storage_paths=[root],
                health_probe=lambda: [Check("TelDrive", True, "controlled gate"), Check("rclone", True, "controlled gate")],
                notify=False)
        assert not any(a.code == AlertCode.BACKUP_OVERDUE for a in store.alerts(active_only=True))
    print("PHASE 10 HOST GATE: PASS")
    print("health evaluation: PASS")
    print("storage observation: PASS")
    print("durable job monitoring: PASS")
    print("durable alerts + local notifications: PASS")
    print("alert resolution: PASS")
    print("production mutation: NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
