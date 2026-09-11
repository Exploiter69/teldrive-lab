"""Phase 9 scheduled backups, snapshots, verification, retention and restore."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .audit import open_audit, record_event
from .jobs import JobStore, JobType
from .runtime import runtime_paths
from .safety import AuthorizationReceipt, Operation, authorize
from .transfer import TransferManager, TransferSpec

SCHEMA_VERSION = 2


class BackupState:
    VERIFIED = "VERIFIED"
    MISSING = "MISSING"
    CORRUPT = "CORRUPT"


@dataclass(frozen=True, slots=True)
class BackupPolicy:
    retention_seconds: int = 30 * 24 * 60 * 60
    safety_window_seconds: int = 7 * 24 * 60 * 60
    interval_seconds: int = 24 * 60 * 60

    def __post_init__(self) -> None:
        if min(self.retention_seconds, self.safety_window_seconds, self.interval_seconds) < 0:
            raise ValueError("backup policy intervals must be non-negative")

    @property
    def effective_retention_seconds(self) -> int:
        return max(self.retention_seconds, self.safety_window_seconds)


@dataclass(frozen=True, slots=True)
class BackupItem:
    source: str
    destination: str
    size: int
    sha256: str


@dataclass(frozen=True, slots=True)
class BackupPlan:
    items: tuple[BackupItem, ...]
    manifest_path: str
    created_at: str
    purge_after: str

    @property
    def digest(self) -> str:
        payload = "\n".join(f"{i.source}|{i.destination}|{i.size}|{i.sha256}" for i in self.items) + f"\n{self.manifest_path}|{self.created_at}|{self.purge_after}"
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class BackupVerification:
    path: str
    expected_sha256: str
    actual_sha256: str | None
    expected_size: int
    actual_size: int | None
    state: str


@dataclass(frozen=True, slots=True)
class BackupReconciliation:
    source: str
    destination: str
    expected_sha256: str
    exists: bool
    size_matches: bool | None
    sha256_matches: bool | None
    state: str


@dataclass(frozen=True, slots=True)
class BackupSchedule:
    schedule_id: str
    sources: tuple[str, ...]
    destination: str
    interval_seconds: int
    next_run_at: float
    enabled: bool = True


class BackupStore:
    """Durable Lab-owned backup and scheduler metadata."""
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else runtime_paths().root / "backups.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS schema_version(version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS backups(digest TEXT PRIMARY KEY, manifest_path TEXT NOT NULL, created_at TEXT NOT NULL, purge_after TEXT NOT NULL, locked INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS backup_items(digest TEXT NOT NULL REFERENCES backups(digest), source TEXT NOT NULL, destination TEXT NOT NULL, size INTEGER NOT NULL, sha256 TEXT NOT NULL, PRIMARY KEY(digest, source));
                CREATE TABLE IF NOT EXISTS schedules(schedule_id TEXT PRIMARY KEY, sources_json TEXT NOT NULL, destination TEXT NOT NULL, interval_seconds INTEGER NOT NULL, next_run_at REAL NOT NULL, enabled INTEGER NOT NULL DEFAULT 1);
            """)
            row = db.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
            if row is None: db.execute("INSERT INTO schema_version VALUES (?)", (SCHEMA_VERSION,))
            elif row[0] != SCHEMA_VERSION: raise RuntimeError(f"unsupported backup schema {row[0]}")

    def put(self, plan: BackupPlan) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT OR REPLACE INTO backups VALUES(?,?,?,?,0)", (plan.digest, plan.manifest_path, plan.created_at, plan.purge_after))
            db.executemany("INSERT OR REPLACE INTO backup_items VALUES(?,?,?,?,?)", [(plan.digest, i.source, i.destination, i.size, i.sha256) for i in plan.items])

    def plans(self) -> tuple[BackupPlan, ...]:
        with sqlite3.connect(self.path) as db:
            rows = db.execute("SELECT digest,manifest_path,created_at,purge_after FROM backups ORDER BY created_at").fetchall()
            result = []
            for digest, manifest, created, purge_after in rows:
                items = db.execute("SELECT source,destination,size,sha256 FROM backup_items WHERE digest=? ORDER BY source", (digest,)).fetchall()
                result.append(BackupPlan(tuple(BackupItem(*row) for row in items), manifest, created, purge_after))
            return tuple(result)

    def lock(self, digest: str) -> None:
        with sqlite3.connect(self.path) as db:
            if not db.execute("UPDATE backups SET locked=1 WHERE digest=?", (digest,)).rowcount: raise KeyError(digest)

    def is_locked(self, digest: str) -> bool:
        with sqlite3.connect(self.path) as db: row = db.execute("SELECT locked FROM backups WHERE digest=?", (digest,)).fetchone()
        return bool(row and row[0])

    def add_schedule(self, schedule: BackupSchedule) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT OR REPLACE INTO schedules VALUES(?,?,?,?,?,?)", (schedule.schedule_id, json.dumps(schedule.sources, sort_keys=True), schedule.destination, schedule.interval_seconds, schedule.next_run_at, int(schedule.enabled)))

    def schedules(self) -> tuple[BackupSchedule, ...]:
        with sqlite3.connect(self.path) as db: rows = db.execute("SELECT * FROM schedules ORDER BY schedule_id").fetchall()
        return tuple(BackupSchedule(r[0], tuple(json.loads(r[1])), r[2], r[3], r[4], bool(r[5])) for r in rows)

    def due_schedules(self, now: float) -> tuple[BackupSchedule, ...]: return tuple(s for s in self.schedules() if s.enabled and s.next_run_at <= now)

    def advance_schedule(self, schedule_id: str, *, now: float) -> None:
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT interval_seconds,next_run_at FROM schedules WHERE schedule_id=?", (schedule_id,)).fetchone()
            if row is None: raise KeyError(schedule_id)
            db.execute("UPDATE schedules SET next_run_at=? WHERE schedule_id=?", (max(row[1] + row[0], now + row[0]), schedule_id))


class BackupPlanner:
    """Read-only deterministic planner. It never authorizes or transfers."""
    @staticmethod
    def _hash(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024): digest.update(chunk)
        return digest.hexdigest()

    def plan(self, sources: list[str | Path] | tuple[str | Path, ...], *, backup_root: str | Path, policy: BackupPolicy | None = None, now: datetime | None = None) -> BackupPlan:
        policy = policy or BackupPolicy(); now = now or datetime.now(timezone.utc); root = Path(backup_root).resolve(); items = []
        for raw in sorted((Path(p) for p in sources), key=lambda p: str(p)):
            source = raw.resolve()
            if not source.is_file(): raise ValueError(f"backup source is not a regular file: {source}")
            destination = (root / source.name).resolve(); decision = authorize(Operation.TRANSFER, source, destination)
            if not decision.allowed and not decision.requires_authorization: raise PermissionError(decision.reason or "protected boundary")
            if destination.exists(): raise FileExistsError(destination)
            items.append(BackupItem(str(source), str(destination), source.stat().st_size, self._hash(source)))
        created = now.isoformat(); purge_after = (now + timedelta(seconds=policy.effective_retention_seconds)).isoformat(); manifest = str((root / "manifests" / f"{now.strftime('%Y%m%dT%H%M%SZ')}.json").resolve())
        return BackupPlan(tuple(items), manifest, created, purge_after)

    @staticmethod
    def manifest(plan: BackupPlan) -> str:
        return json.dumps({"schema": 1, "digest": plan.digest, "created_at": plan.created_at, "purge_after": plan.purge_after, "items": [asdict(i) for i in plan.items]}, sort_keys=True, separators=(",", ":"))

    def snapshot_plan(self, sources: list[str | Path] | tuple[str | Path, ...], *, snapshot_root: str | Path, now: datetime | None = None) -> BackupPlan:
        return self.plan(sources, backup_root=Path(snapshot_root) / "snapshot", policy=BackupPolicy(retention_seconds=365 * 24 * 60 * 60, safety_window_seconds=7 * 24 * 60 * 60), now=now)


class BackupExecutor:
    def __init__(self, store: BackupStore | None = None, transfer: TransferManager | None = None) -> None: self.store = store or BackupStore(); self.transfer = transfer or TransferManager()
    @staticmethod
    def _audit(operation: str, **kwargs: object) -> None:
        conn = open_audit(runtime_paths().root / "audit.db")
        try: record_event(conn, event_id=str(uuid.uuid4()), operation=operation, **kwargs)
        finally: conn.close()

    def apply(self, plan: BackupPlan, *, authorization_id: str) -> tuple[bool, tuple[str, ...]]:
        changed = []
        for item in plan.items:
            receipt = AuthorizationReceipt.for_paths(Operation.TRANSFER, item.source, item.destination, authorization_id=authorization_id); result = self.transfer.transfer(TransferSpec(item.source, item.destination), authorization=receipt)
            if not result.success or not result.verified or result.destination_sha256 != item.sha256: self._audit("BACKUP", source=item.source, destination=item.destination, decision="ALLOW", result="FAILED", error_code="BACKUP_VERIFY"); return False, tuple(changed)
            changed.append(item.destination)
        manifest = Path(plan.manifest_path); manifest.parent.mkdir(parents=True, exist_ok=True); manifest.write_text(BackupPlanner.manifest(plan), encoding="utf-8"); self.store.put(plan)
        self._audit("BACKUP", decision="ALLOW", result="SUCCESS", details={"digest": plan.digest, "items": len(plan.items), "authorization_id": authorization_id}); return True, tuple(changed)

    def verify(self, plan: BackupPlan) -> tuple[BackupVerification, ...]:
        results = []
        for item in plan.items:
            path = Path(item.destination)
            if not path.is_file(): results.append(BackupVerification(item.destination, item.sha256, None, item.size, None, BackupState.MISSING)); continue
            size = path.stat().st_size; actual = BackupPlanner._hash(path); state = BackupState.VERIFIED if size == item.size and actual == item.sha256 else BackupState.CORRUPT; results.append(BackupVerification(item.destination, item.sha256, actual, item.size, size, state))
        self._audit("BACKUP_VERIFY", decision="ALLOW", result="SUCCESS", details={"verified": sum(x.state == BackupState.VERIFIED for x in results), "total": len(results)}); return tuple(results)

    def reconcile(self, plan: BackupPlan) -> tuple[BackupReconciliation, ...]:
        results = []
        for item in plan.items:
            path = Path(item.destination)
            if not path.is_file(): results.append(BackupReconciliation(item.source, item.destination, item.sha256, False, None, None, BackupState.MISSING)); continue
            size = path.stat().st_size; actual = BackupPlanner._hash(path); ok = size == item.size and actual == item.sha256; results.append(BackupReconciliation(item.source, item.destination, item.sha256, True, size == item.size, actual == item.sha256, BackupState.VERIFIED if ok else BackupState.CORRUPT))
        return tuple(results)

    def restore(self, plan: BackupPlan, *, restore_root: str | Path, authorization_id: str) -> tuple[bool, tuple[str, ...]]:
        restored = []
        for item in plan.items:
            source = Path(item.destination); destination = (Path(restore_root).resolve() / Path(item.source).name).resolve()
            if destination.exists(): self._audit("BACKUP_RESTORE", source=str(source), destination=str(destination), decision="DENY", result="BLOCKED", error_code="DESTINATION_EXISTS"); return False, tuple(restored)
            if not source.is_file() or BackupPlanner._hash(source) != item.sha256: self._audit("BACKUP_RESTORE", source=str(source), destination=str(destination), decision="DENY", result="BLOCKED", error_code="BACKUP_NOT_VERIFIED"); return False, tuple(restored)
            receipt = AuthorizationReceipt.for_paths(Operation.TRANSFER, source, destination, authorization_id=authorization_id); result = self.transfer.transfer(TransferSpec(str(source), str(destination)), authorization=receipt)
            if not result.success or not result.verified or result.destination_sha256 != item.sha256: self._audit("BACKUP_RESTORE", source=str(source), destination=str(destination), decision="ALLOW", result="FAILED", error_code="RESTORE_VERIFY"); return False, tuple(restored)
            restored.append(str(destination))
        self._audit("BACKUP_RESTORE", decision="ALLOW", result="SUCCESS", details={"items": len(restored), "authorization_id": authorization_id}); return True, tuple(restored)

    def retention_ready(self, *, now: datetime | None = None) -> tuple[BackupPlan, ...]:
        now = now or datetime.now(timezone.utc); return tuple(p for p in self.store.plans() if datetime.fromisoformat(p.purge_after) <= now and not self.store.is_locked(p.digest))

    def purge(self, plan: BackupPlan, *, authorization_id: str) -> tuple[bool, tuple[str, ...]]:
        if self.store.is_locked(plan.digest) or datetime.fromisoformat(plan.purge_after) > datetime.now(timezone.utc): return False, ()
        removed = []
        for item in plan.items:
            path = Path(item.destination).resolve(); receipt = AuthorizationReceipt.for_paths(Operation.DELETE, path, authorization_id=authorization_id); decision = authorize(Operation.DELETE, path, receipt=receipt)
            if not decision.allowed: return False, tuple(removed)
            if path.exists(): path.unlink(); removed.append(str(path))
        manifest = Path(plan.manifest_path)
        if manifest.exists(): manifest.unlink()
        self._audit("BACKUP_PURGE", decision="ALLOW", result="SUCCESS", details={"digest": plan.digest, "authorization_id": authorization_id}); return True, tuple(removed)


class BackupScheduler:
    """Deterministic scheduler facade; an external timer/systemd may call run_due()."""
    def __init__(self, store: BackupStore | None = None, jobs: JobStore | None = None) -> None: self.store = store or BackupStore(); self.jobs = jobs or JobStore(runtime_paths().root / "jobs.db")
    def add(self, sources: list[str | Path] | tuple[str | Path, ...], destination: str | Path, *, interval_seconds: int = 24 * 60 * 60, first_run_at: float | None = None) -> BackupSchedule:
        if interval_seconds <= 0: raise ValueError("interval_seconds must be positive")
        schedule = BackupSchedule(uuid.uuid4().hex, tuple(sorted(str(Path(p).resolve()) for p in sources)), str(Path(destination).resolve()), interval_seconds, first_run_at if first_run_at is not None else datetime.now(timezone.utc).timestamp()); self.store.add_schedule(schedule); return schedule
    def run_due(self, *, now: float | None = None) -> tuple[str, ...]:
        now = now if now is not None else datetime.now(timezone.utc).timestamp(); created = []
        for schedule in self.store.due_schedules(now):
            job = self.jobs.enqueue(JobType.BACKUP, source=json.dumps(schedule.sources, separators=(",", ":")), destination=schedule.destination); created.append(job.job_id); self.store.advance_schedule(schedule.schedule_id, now=now)
        return tuple(created)


def schedule_backup(job_store: JobStore, *, sources: list[str | Path] | tuple[str | Path, ...], destination: str | Path) -> str:
    source_payload = json.dumps(sorted(str(Path(p).resolve()) for p in sources), separators=(",", ":")); return job_store.enqueue(JobType.BACKUP, source=source_payload, destination=str(Path(destination).resolve())).job_id
