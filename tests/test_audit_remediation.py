from __future__ import annotations

import subprocess
import time
from dataclasses import replace
from pathlib import Path

from teldrive_lab.backups import BackupExecutor, BackupPlanner, BackupStore, backup_metadata_root
from teldrive_lab.jobs import JobState, JobStore, JobType
from teldrive_lab.lifecycle import LifecycleExecutor, LifecyclePlanItem, LifecyclePlanner, LifecycleRecord, LifecycleAction, LifecycleStore
from teldrive_lab.rclone import RcloneAdapter
from teldrive_lab.safety import AuthorizationReceipt, Operation
from teldrive_lab.transfer_executor import TransferJobExecutor
from teldrive_lab.worker import Worker


def test_expired_transfer_with_matching_destination_is_completed_not_replayed(tmp_path: Path):
    source = tmp_path / "source.bin"
    destination = tmp_path / "destination.bin"
    source.write_bytes(b"durable-side-effect")
    destination.write_bytes(source.read_bytes())
    store = JobStore(tmp_path / "jobs.db")
    job = store.enqueue(JobType.UPLOAD, source=str(source), destination=str(destination), checksum=None, max_attempts=3)
    claimed = store.claim("dead-worker", lease_seconds=0.01)
    assert claimed is not None
    time.sleep(0.03)
    executor = TransferJobExecutor()
    assert store.recover_expired_leases(reconciler=executor.reconcile) == 1
    recovered = store.get(job.job_id)
    assert recovered.state is JobState.COMPLETED
    assert destination.read_bytes() == source.read_bytes()
    assert recovered.idempotency_key


def test_expired_transfer_without_identifiable_existing_destination_fails_closed(tmp_path: Path):
    source = tmp_path / "source.bin"
    destination = tmp_path / "destination.bin"
    source.write_bytes(b"source")
    destination.write_bytes(b"different")
    store = JobStore(tmp_path / "jobs.db")
    job = store.enqueue(JobType.UPLOAD, source=str(source), destination=str(destination), checksum="not-the-real-checksum")
    assert store.claim("dead-worker", lease_seconds=0.01)
    time.sleep(0.03)
    assert store.recover_expired_leases(reconciler=TransferJobExecutor().reconcile) == 1
    assert store.get(job.job_id).state is JobState.FAILED


def test_worker_unknown_job_type_fails_closed(tmp_path: Path):
    store = JobStore(tmp_path / "jobs.db")
    job = store.enqueue(JobType.UPLOAD, source=str(tmp_path / "s"), destination=str(tmp_path / "d"))
    store._connect().close()
    conn = store._connect()
    try:
        conn.execute("UPDATE jobs SET type='UNKNOWN_FUTURE_TYPE' WHERE job_id=?", (job.job_id,))
        conn.commit()
    finally:
        conn.close()
    # The durable row is intentionally invalid; claim remains possible but safety must deny.
    # Build the in-memory job without relying on JobType conversion in JobStore._row.
    from types import SimpleNamespace
    fake = SimpleNamespace(type=SimpleNamespace(value="UNKNOWN_FUTURE_TYPE"), source=job.source, destination=job.destination, path=None)
    worker = Worker(store, object())
    decision = worker._safety_decision(fake)  # type: ignore[arg-type]
    assert not decision.allowed
    assert "unsupported job type" in decision.reason


def test_lifecycle_stale_purge_plan_is_blocked(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TELDRIVE_LAB_STATE", str(tmp_path / "state"))
    quarantine = tmp_path / "quarantine.bin"
    quarantine.write_bytes(b"keep me")
    source = tmp_path / "source.bin"
    source.write_bytes(b"source")
    store = LifecycleStore(tmp_path / "lifecycle.db")
    import hashlib
    digest = hashlib.sha256(quarantine.read_bytes()).hexdigest()
    from datetime import datetime, timezone
    record = LifecycleRecord(str(source), str(quarantine), quarantine.stat().st_size, digest, datetime.now(timezone.utc).isoformat(), "1970-01-01T00:00:00+00:00")
    store.put(record)
    plan = LifecyclePlanner(store).purge_plan(now=datetime.now(timezone.utc))
    store.set_locked(str(source), True)
    ok, removed = LifecycleExecutor(store=store).purge(plan, authorization_id="test")
    assert not ok
    assert not removed
    assert quarantine.exists()


def test_backup_rejects_manifest_outside_lab_root_before_copy(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TELDRIVE_LAB_STATE", str(tmp_path / "state"))
    source = tmp_path / "source.bin"
    source.write_bytes(b"backup")
    backup_root = tmp_path / "backups"
    plan = BackupPlanner().plan([source], backup_root=backup_root)
    forged = replace(plan, manifest_path=str(tmp_path / "attacker-owned.json"))
    executor = BackupExecutor(store=BackupStore(tmp_path / "backups.db"))
    ok, changed = executor.apply(forged, authorization_id="test")
    assert not ok
    assert not changed
    assert not (tmp_path / "attacker-owned.json").exists()
    assert not (backup_root / source.name).exists()
    assert backup_metadata_root().is_dir()


def test_backup_purge_revalidates_locked_plan(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TELDRIVE_LAB_STATE", str(tmp_path / "state"))
    source = tmp_path / "source.bin"
    source.write_bytes(b"backup")
    plan = BackupPlanner().plan([source], backup_root=tmp_path / "backups")
    store = BackupStore(tmp_path / "backups.db")
    # Persist the plan and create the metadata file without touching production state.
    manifest = Path(plan.manifest_path)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(BackupPlanner.manifest(plan), encoding="utf-8")
    store.put(plan)
    destination = Path(plan.items[0].destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())
    store.lock(plan.digest)
    ok, removed = BackupExecutor(store=store).purge(plan, authorization_id="test")
    assert not ok
    assert not removed
    assert destination.exists()
    assert manifest.exists()


def test_rclone_protected_remote_is_blocked_before_runner():
    calls = []
    def runner(command, *args):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")
    adapter = RcloneAdapter(runner=runner)
    result = adapter.copy("/tmp/source", "teldrive:production/path", authorization=AuthorizationReceipt.for_paths(Operation.TRANSFER, "/tmp/source", "teldrive:production/path", authorization_id="test"))
    assert not result.success
    assert "protected production rclone remote" in (result.error or "")
    assert calls == []


def test_rclone_runner_receives_timeout():
    calls = []
    def runner(command, timeout):
        calls.append((command, timeout))
        return subprocess.CompletedProcess(command, 0, "", "")
    adapter = RcloneAdapter(runner=runner, timeout_seconds=7)
    result = adapter.copy("/tmp/source", "/tmp/destination", dry_run=True)
    assert result.success
    assert calls and calls[0][1] == 7
