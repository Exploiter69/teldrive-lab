from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from teldrive_lab.health import Check
from teldrive_lab.monitoring import AlertCode, MonitoringStore, collect, evaluate, job_snapshot, storage_snapshot


def make_jobs(path: Path, *, running: bool = False, stuck: bool = False) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE jobs (state TEXT, updated REAL, worker_id TEXT, lease_until REAL)")
        updated = time.time() - (7200 if stuck else 1)
        conn.execute("INSERT INTO jobs VALUES (?,?,?,?)", ("RUNNING" if running else "QUEUED", updated, "worker-1" if running else None, None))
        conn.execute("INSERT INTO jobs VALUES (?,?,?,?)", ("COMPLETED", time.time(), None, None))


def test_storage_snapshot_is_read_only(tmp_path: Path) -> None:
    before = list(tmp_path.iterdir())
    snap = storage_snapshot(tmp_path)
    assert snap.total_bytes >= snap.used_bytes >= 0
    assert snap.free_bytes >= 0
    assert list(tmp_path.iterdir()) == before


def test_job_snapshot_detects_stuck(tmp_path: Path) -> None:
    db = tmp_path / "jobs.db"
    make_jobs(db, running=True, stuck=True)
    snap = job_snapshot(db)
    assert snap.total == 2
    assert snap.running == 1
    assert snap.completed == 1
    assert snap.stuck == 1
    assert snap.workers == 1


def test_evaluate_disk_and_health_alerts(tmp_path: Path) -> None:
    storage = storage_snapshot(tmp_path)
    forced = type(storage)(storage.path, storage.total_bytes, storage.used_bytes, storage.free_bytes, 2.0)
    candidates = evaluate(
        health=[Check("TelDrive", False, "offline")],
        storage=[forced],
        jobs=job_snapshot(tmp_path / "missing.db"),
    )
    codes = {item[0] for item in candidates}
    assert AlertCode.DISK_SPACE_CRITICAL in codes
    assert AlertCode.TELDRIVE_UNHEALTHY in codes


def test_collect_persists_alert_and_local_notification(tmp_path: Path) -> None:
    store = MonitoringStore(tmp_path / "monitor.db")
    jobs = tmp_path / "jobs.db"
    make_jobs(jobs)
    audit = tmp_path / "audit.db"
    snapshot = collect(
        store=store,
        audit_path=audit,
        job_db=jobs,
        storage_paths=[tmp_path],
        health_probe=lambda: [Check("TelDrive", False, "offline")],
    )
    assert any(a.code == AlertCode.TELDRIVE_UNHEALTHY for a in snapshot.alerts)
    alerts = store.alerts(active_only=True)
    assert alerts
    with sqlite3.connect(store.path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0] >= 1
        assert conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] >= 1


def test_alert_resolves_when_condition_disappears(tmp_path: Path) -> None:
    store = MonitoringStore(tmp_path / "monitor.db")
    jobs = tmp_path / "jobs.db"
    make_jobs(jobs)
    probe = lambda: [Check("TelDrive", False, "offline")]
    collect(store=store, audit_path=tmp_path / "audit.db", job_db=jobs, storage_paths=[tmp_path], health_probe=probe, notify=False)
    assert store.alerts(active_only=True)
    collect(store=store, audit_path=tmp_path / "audit.db", job_db=jobs, storage_paths=[tmp_path], health_probe=lambda: [Check("TelDrive", True, "ok")], notify=False)
    assert store.alerts(active_only=True) == []
    assert store.alerts(active_only=False)
