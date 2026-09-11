from __future__ import annotations

import os
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from teldrive_lab.lifecycle import LifecycleAction, LifecycleExecutor, LifecyclePlanner, LifecycleStore, RetentionPolicy


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"{message}: PASS")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="teldrive-lab-phase8-") as raw:
        root = Path(raw)
        os.environ["TELDRIVE_LAB_STATE"] = str(root / "runtime")
        source = root / "source.bin"
        quarantine = root / "quarantine"
        restore = root / "restore"
        source.write_bytes(b"phase8 lifecycle host gate")
        store = LifecycleStore(root / "lifecycle.db")
        planner = LifecyclePlanner(store)
        executor = LifecycleExecutor(store)
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)

        plan = planner.quarantine_plan(
            [source], quarantine_root=quarantine,
            policy=RetentionPolicy(retention_seconds=60, safety_window_seconds=60), now=now,
        )
        check(plan.items[0].action is LifecycleAction.QUARANTINE, "deterministic quarantine plan")
        check(plan.items[0].sha256 is not None, "quarantine plan has SHA-256 evidence")
        check(plan.items[0].purge_after == (now + timedelta(seconds=60)).isoformat(), "retention window is enforced")

        ok, copied = executor.quarantine(plan, authorization_id="phase8-host-quarantine")
        check(ok and copied, "isolated quarantine copy + verification")
        check(source.exists(), "quarantine preserves source")
        check(Path(copied[0]).read_bytes() == source.read_bytes(), "quarantine content verified")
        check(planner.reconcile()[0].state == "VERIFIED", "read-only recovery reconciliation")

        blocked = planner.purge_plan(now=now)
        check(blocked.items[0].action is LifecycleAction.PURGE_BLOCKED, "safety window blocks early purge")

        locked_record = store.get(str(source.resolve()))
        check(locked_record is not None, "lifecycle metadata persisted")
        store.set_locked(locked_record.source, True)
        locked = planner.purge_plan(now=now + timedelta(days=30))
        check(locked.items[0].action is LifecycleAction.LOCKED, "immutable lock blocks purge")
        store.set_locked(locked_record.source, False)

        restore_plan = planner.restore_plan(destination_root=restore)
        check(restore_plan.items[0].action is LifecycleAction.RESTORE, "restore plan is non-overwriting")
        ok, restored = executor.restore(restore_plan, authorization_id="phase8-host-restore")
        check(ok and restored, "isolated restore + verification")
        check(Path(restored[0]).read_bytes() == source.read_bytes(), "restore checksum preserved")

        ready = planner.purge_plan(now=now + timedelta(seconds=61))
        check(ready.items[0].action is LifecycleAction.PURGE_READY, "expired retention becomes purge-ready")
        ok, removed = executor.purge(ready, authorization_id="phase8-host-purge")
        check(ok and removed and not Path(removed[0]).exists(), "explicit quarantine purge")
        check(source.exists(), "purge never deletes original source")

        with sqlite3.connect(root / "runtime" / "audit.db") as db:
            operations = [row[0] for row in db.execute("SELECT operation FROM events ORDER BY id")]
        check(operations == ["QUARANTINE", "RESTORE", "PURGE"], "lifecycle actions are audited")

        protected = planner.quarantine_plan(
            ["/home/thakuralok/TelegramRaw/phase8-host-gate-do-not-create"],
            quarantine_root=root / "protected-quarantine",
        )
        check(protected.items[0].action is LifecycleAction.PURGE_BLOCKED,
              "protected production destination/source is blocked")

    print("PHASE 8 HOST GATE: PASS")
    print("production storage mutation: NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
