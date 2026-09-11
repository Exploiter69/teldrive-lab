from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from teldrive_lab.lifecycle import (
    LifecycleAction,
    LifecycleExecutor,
    LifecyclePlanner,
    LifecycleStore,
    RetentionPolicy,
    lock_records,
)


def test_quarantine_is_deterministic_and_preserves_source(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    quarantine = tmp_path / "quarantine"
    source.write_text("phase8")
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    plan = LifecyclePlanner(LifecycleStore(tmp_path / "lifecycle.db")).quarantine_plan(
        [source], quarantine_root=quarantine,
        policy=RetentionPolicy(safety_window_seconds=60), now=now,
    )
    assert plan.quarantine_count == 1
    item = plan.items[0]
    assert item.action is LifecycleAction.QUARANTINE
    assert item.sha256
    assert item.purge_after == (now + timedelta(seconds=60)).isoformat()
    assert source.read_text() == "phase8"


def test_protected_source_is_blocked(tmp_path: Path) -> None:
    store = LifecycleStore(tmp_path / "lifecycle.db")
    plan = LifecyclePlanner(store).quarantine_plan(
        ["/home/thakuralok/TelegramRaw/not-real.txt"],
        quarantine_root=tmp_path / "quarantine",
    )
    assert plan.items[0].action is LifecycleAction.PURGE_BLOCKED
    assert "source" in plan.items[0].reason


def test_quarantine_restore_and_verification(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    quarantine = tmp_path / "quarantine"
    restore = tmp_path / "restore"
    source.write_bytes(b"verified lifecycle data")
    store = LifecycleStore(tmp_path / "lifecycle.db")
    planner = LifecyclePlanner(store)
    executor = LifecycleExecutor(store)

    plan = planner.quarantine_plan([source], quarantine_root=quarantine,
                                   policy=RetentionPolicy(safety_window_seconds=0))
    ok, paths = executor.quarantine(plan, authorization_id="test-quarantine")
    assert ok and paths
    assert source.exists()
    assert Path(paths[0]).read_bytes() == source.read_bytes()

    restore_plan = planner.restore_plan(destination_root=restore)
    assert restore_plan.items[0].action is LifecycleAction.RESTORE
    ok, restored = executor.restore(restore_plan, authorization_id="test-restore")
    assert ok and restored
    assert Path(restored[0]).read_bytes() == source.read_bytes()


def test_purge_respects_safety_window_and_lock(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    quarantine = tmp_path / "quarantine"
    source.write_text("protected by time")
    store = LifecycleStore(tmp_path / "lifecycle.db")
    planner = LifecyclePlanner(store)
    executor = LifecycleExecutor(store)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    plan = planner.quarantine_plan([source], quarantine_root=quarantine,
                                   policy=RetentionPolicy(safety_window_seconds=3600), now=now)
    ok, _ = executor.quarantine(plan, authorization_id="test-quarantine")
    assert ok

    blocked = planner.purge_plan(now=now)
    assert blocked.items[0].action is LifecycleAction.PURGE_BLOCKED

    record = store.get(str(source.resolve()))
    assert record is not None
    store.set_locked(record.source, True)
    locked = planner.purge_plan(now=now + timedelta(days=2))
    assert locked.items[0].action is LifecycleAction.LOCKED


def test_expired_unlocked_quarantine_can_be_explicitly_purged(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    quarantine = tmp_path / "quarantine"
    source.write_text("purge me")
    store = LifecycleStore(tmp_path / "lifecycle.db")
    planner = LifecyclePlanner(store)
    executor = LifecycleExecutor(store)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    plan = planner.quarantine_plan([source], quarantine_root=quarantine,
                                   policy=RetentionPolicy(safety_window_seconds=1), now=now)
    ok, paths = executor.quarantine(plan, authorization_id="test-quarantine")
    assert ok and paths

    ready = planner.purge_plan(now=now + timedelta(seconds=2))
    assert ready.items[0].action is LifecycleAction.PURGE_READY
    ok, removed = executor.purge(ready, authorization_id="test-purge")
    assert ok and removed
    assert not Path(removed[0]).exists()
    assert source.exists()


def test_lock_records_requires_existing_record(tmp_path: Path) -> None:
    store = LifecycleStore(tmp_path / "lifecycle.db")
    try:
        lock_records(store, [str(tmp_path / "missing")])
    except ValueError as exc:
        assert "no lifecycle record" in str(exc)
    else:
        raise AssertionError("missing lifecycle record must fail closed")
