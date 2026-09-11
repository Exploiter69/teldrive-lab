from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from teldrive_lab.backups import BackupExecutor, BackupPlanner, BackupPolicy, BackupState, BackupStore, BackupScheduler
from teldrive_lab.jobs import JobStore


def test_backup_plan_is_deterministic_and_manifest_is_stable(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("backup-me")
    root = tmp_path / "backup"
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    planner = BackupPlanner()
    plan = planner.plan([source], backup_root=root, now=now)
    assert plan.items[0].size == 9
    assert len(plan.items[0].sha256) == 64
    assert plan.purge_after > plan.created_at
    manifest = planner.manifest(plan)
    assert plan.digest in manifest
    assert '"source":' in manifest


def test_backup_apply_verify_reconcile_and_restore(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELDRIVE_LAB_ROOT", str(tmp_path / "runtime"))
    source = tmp_path / "source.txt"
    source.write_text("verified backup")
    backup_root = tmp_path / "backups"
    restore_root = tmp_path / "restore"
    plan = BackupPlanner().plan([source], backup_root=backup_root,
                                policy=BackupPolicy(retention_seconds=100, safety_window_seconds=10),
                                now=datetime(2026, 1, 1, tzinfo=timezone.utc))
    executor = BackupExecutor(BackupStore(tmp_path / "backups.db"))
    ok, changed = executor.apply(plan, authorization_id="test")
    assert ok and changed
    assert executor.verify(plan)[0].state == BackupState.VERIFIED
    assert executor.reconcile(plan)[0].state == BackupState.VERIFIED
    ok, restored = executor.restore(plan, restore_root=restore_root, authorization_id="test")
    assert ok and restored
    assert Path(restored[0]).read_text() == source.read_text()


def test_corruption_and_missing_are_detected(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"abc")
    plan = BackupPlanner().plan([source], backup_root=tmp_path / "backup")
    executor = BackupExecutor(BackupStore(tmp_path / "db.sqlite"))
    ok, _ = executor.apply(plan, authorization_id="test")
    assert ok
    Path(plan.items[0].destination).write_bytes(b"changed")
    assert executor.verify(plan)[0].state == BackupState.CORRUPT
    Path(plan.items[0].destination).unlink()
    assert executor.verify(plan)[0].state == BackupState.MISSING


def test_retention_cannot_bypass_safety_window(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x")
    created = datetime(2026, 1, 1, tzinfo=timezone.utc)
    plan = BackupPlanner().plan([source], backup_root=tmp_path / "backup",
                                policy=BackupPolicy(retention_seconds=0, safety_window_seconds=3600), now=created)
    assert plan.purge_after == "2026-01-01T01:00:00+00:00"


def test_locked_backup_is_not_retention_ready(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x")
    plan = BackupPlanner().plan([source], backup_root=tmp_path / "backup",
                                policy=BackupPolicy(retention_seconds=1, safety_window_seconds=0),
                                now=datetime(2026, 1, 1, tzinfo=timezone.utc))
    store = BackupStore(tmp_path / "db.sqlite")
    executor = BackupExecutor(store)
    assert executor.apply(plan, authorization_id="test")[0]
    store.lock(plan.digest)
    assert executor.retention_ready(now=datetime(2026, 1, 2, tzinfo=timezone.utc)) == ()


def test_scheduler_persists_and_enqueues_due_backup(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x")
    store = BackupStore(tmp_path / "backup.db")
    jobs = JobStore(tmp_path / "jobs.db")
    scheduler = BackupScheduler(store, jobs)
    schedule = scheduler.add([source], tmp_path / "destination", interval_seconds=60, first_run_at=10)
    assert len(store.schedules()) == 1
    ids = scheduler.run_due(now=10)
    assert len(ids) == 1
    assert jobs.get(ids[0]).destination == str((tmp_path / "destination").resolve())
    assert not store.due_schedules(10)
    assert schedule.schedule_id == store.schedules()[0].schedule_id


def test_restore_never_overwrites_existing_destination(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("original")
    restore = tmp_path / "restore"
    restore.mkdir()
    (restore / source.name).write_text("keep")
    plan = BackupPlanner().plan([source], backup_root=tmp_path / "backup")
    executor = BackupExecutor(BackupStore(tmp_path / "db.sqlite"))
    assert executor.apply(plan, authorization_id="test")[0]
    ok, restored = executor.restore(plan, restore_root=restore, authorization_id="test")
    assert not ok and restored == ()
    assert (restore / source.name).read_text() == "keep"
