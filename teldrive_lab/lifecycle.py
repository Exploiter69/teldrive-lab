"""Phase 8 safety and lifecycle management."""

from __future__ import annotations

import hashlib
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from pathlib import Path
from typing import Iterable

from .audit import open_audit, record_event
from .runtime import runtime_paths
from .safety import AuthorizationReceipt, Operation, authorize
from .transfer import TransferManager, TransferSpec

SCHEMA_VERSION = 1


class LifecycleAction(StrEnum):
    KEEP = "KEEP"
    QUARANTINE = "QUARANTINE"
    PURGE_READY = "PURGE_READY"
    PURGE_BLOCKED = "PURGE_BLOCKED"
    LOCKED = "LOCKED"
    RESTORE = "RESTORE"


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    retention_seconds: int = 30 * 24 * 60 * 60
    safety_window_seconds: int = 7 * 24 * 60 * 60

    def __post_init__(self) -> None:
        if self.retention_seconds < 0 or self.safety_window_seconds < 0:
            raise ValueError("retention and safety windows must be non-negative")

    @property
    def effective_retention_seconds(self) -> int:
        """Purge cannot become eligible before either protection interval expires."""
        return max(self.retention_seconds, self.safety_window_seconds)


@dataclass(frozen=True, slots=True)
class LifecycleRecord:
    source: str
    quarantine: str
    size: int
    sha256: str
    quarantined_at: str
    purge_after: str
    locked: bool = False


@dataclass(frozen=True, slots=True)
class LifecyclePlanItem:
    source: str
    quarantine: str
    action: LifecycleAction
    reason: str
    size: int
    sha256: str | None
    purge_after: str | None
    destination: str | None = None


@dataclass(frozen=True, slots=True)
class LifecyclePlan:
    items: tuple[LifecyclePlanItem, ...]

    @property
    def digest(self) -> str:
        payload = "\n".join(
            f"{item.source}|{item.quarantine}|{item.destination or ''}|{item.action.value}|{item.size}|{item.sha256 or ''}|{item.purge_after or ''}"
            for item in self.items
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    @property
    def quarantine_count(self) -> int:
        return sum(item.action is LifecycleAction.QUARANTINE for item in self.items)

    @property
    def purge_ready_count(self) -> int:
        return sum(item.action is LifecycleAction.PURGE_READY for item in self.items)

    @property
    def blocked_count(self) -> int:
        return sum(item.action is LifecycleAction.PURGE_BLOCKED for item in self.items)


@dataclass(frozen=True, slots=True)
class LifecycleReconciliation:
    source: str
    quarantine: str
    source_exists: bool
    quarantine_exists: bool
    size_matches: bool | None
    sha256_matches: bool | None
    locked: bool
    state: str
    reason: str


class LifecycleStore:
    """Durable Lab-owned lifecycle metadata; never TelDrive state."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else runtime_paths().root / "lifecycle.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS lifecycle (
                    source TEXT PRIMARY KEY,
                    quarantine TEXT NOT NULL UNIQUE,
                    size INTEGER NOT NULL,
                    sha256 TEXT NOT NULL,
                    quarantined_at TEXT NOT NULL,
                    purge_after TEXT NOT NULL,
                    locked INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_lifecycle_purge_after ON lifecycle(purge_after);
                """
            )
            row = db.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
            if row is None:
                db.execute("INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,))
            elif row[0] != SCHEMA_VERSION:
                raise RuntimeError(f"unsupported lifecycle schema {row[0]}")

    def put(self, record: LifecycleRecord) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute(
                """INSERT INTO lifecycle(source,quarantine,size,sha256,quarantined_at,purge_after,locked)
                   VALUES(?,?,?,?,?,?,?)
                   ON CONFLICT(source) DO UPDATE SET quarantine=excluded.quarantine,
                   size=excluded.size, sha256=excluded.sha256, quarantined_at=excluded.quarantined_at,
                   purge_after=excluded.purge_after, locked=excluded.locked""",
                (record.source, record.quarantine, record.size, record.sha256,
                 record.quarantined_at, record.purge_after, int(record.locked)),
            )

    def get(self, source: str) -> LifecycleRecord | None:
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT * FROM lifecycle WHERE source=?", (source,)).fetchone()
        if row is None:
            return None
        return LifecycleRecord(row[0], row[1], row[2], row[3], row[4], row[5], bool(row[6]))

    def all(self) -> tuple[LifecycleRecord, ...]:
        with sqlite3.connect(self.path) as db:
            rows = db.execute("SELECT * FROM lifecycle ORDER BY source").fetchall()
        return tuple(LifecycleRecord(r[0], r[1], r[2], r[3], r[4], r[5], bool(r[6])) for r in rows)

    def set_locked(self, source: str, locked: bool = True) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE lifecycle SET locked=? WHERE source=?", (int(locked), source))


class LifecyclePlanner:
    """Build deterministic lifecycle plans; authorization is a later phase."""

    def __init__(self, store: LifecycleStore | None = None) -> None:
        self.store = store or LifecycleStore()

    @staticmethod
    def _hash(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
        return digest.hexdigest()

    def quarantine_plan(self, paths: Iterable[str | Path], *, quarantine_root: str | Path,
                       policy: RetentionPolicy | None = None, now: datetime | None = None) -> LifecyclePlan:
        policy = policy or RetentionPolicy()
        now = now or datetime.now(timezone.utc)
        root = Path(quarantine_root).resolve()
        items: list[LifecyclePlanItem] = []
        for raw in sorted((Path(p) for p in paths), key=lambda p: str(p)):
            target = raw.resolve()
            destination = (root / raw.name).resolve()
            decision = authorize(Operation.TRANSFER, target, destination)
            if not target.is_file():
                items.append(LifecyclePlanItem(str(target), str(destination), LifecycleAction.PURGE_BLOCKED,
                                               "source is not a regular file", 0, None, None))
                continue
            if not decision.allowed and not decision.requires_authorization:
                items.append(LifecyclePlanItem(str(target), str(destination), LifecycleAction.PURGE_BLOCKED,
                                               decision.reason or "protected production boundary", target.stat().st_size, None, None))
                continue
            if destination.exists():
                items.append(LifecyclePlanItem(str(target), str(destination), LifecycleAction.PURGE_BLOCKED,
                                               "quarantine destination already exists", target.stat().st_size, None, None))
                continue
            size = target.stat().st_size
            digest = self._hash(target)
            purge_after = now + timedelta(seconds=policy.effective_retention_seconds)
            items.append(LifecyclePlanItem(str(target), str(destination), LifecycleAction.QUARANTINE,
                                           "explicit authorization required to quarantine; source remains intact",
                                           size, digest, purge_after.isoformat()))
        return LifecyclePlan(tuple(items))

    def purge_plan(self, *, now: datetime | None = None) -> LifecyclePlan:
        now = now or datetime.now(timezone.utc)
        items: list[LifecyclePlanItem] = []
        for record in self.store.all():
            quarantine = Path(record.quarantine)
            if record.locked:
                action, reason = LifecycleAction.LOCKED, "immutable lifecycle lock"
            elif not quarantine.is_file():
                action, reason = LifecycleAction.PURGE_BLOCKED, "quarantine copy is missing"
            elif datetime.fromisoformat(record.purge_after) > now:
                action, reason = LifecycleAction.PURGE_BLOCKED, "retention/safety window has not elapsed"
            else:
                action, reason = LifecycleAction.PURGE_READY, "retention and safety windows elapsed"
            items.append(LifecyclePlanItem(record.source, record.quarantine, action, reason,
                                           record.size, record.sha256, record.purge_after))
        return LifecyclePlan(tuple(items))

    def restore_plan(self, *, destination_root: str | Path, sources: Iterable[str | Path] | None = None) -> LifecyclePlan:
        selected = {str(Path(p).resolve()) for p in sources} if sources else None
        items: list[LifecyclePlanItem] = []
        for record in self.store.all():
            if selected is not None and str(Path(record.quarantine).resolve()) not in selected:
                continue
            source = Path(record.quarantine)
            destination = (Path(destination_root) / Path(record.source).name).resolve()
            if not source.is_file():
                items.append(LifecyclePlanItem(record.source, record.quarantine, LifecycleAction.PURGE_BLOCKED,
                                               "quarantine copy is missing", record.size, record.sha256, record.purge_after,
                                               str(destination)))
                continue
            if destination.exists():
                items.append(LifecyclePlanItem(record.source, record.quarantine, LifecycleAction.PURGE_BLOCKED,
                                               "restore destination exists; overwrite is forbidden", record.size, record.sha256, record.purge_after,
                                               str(destination)))
                continue
            decision = authorize(Operation.TRANSFER, source, destination)
            if not decision.allowed and not decision.requires_authorization:
                items.append(LifecyclePlanItem(record.source, record.quarantine, LifecycleAction.PURGE_BLOCKED,
                                               decision.reason or "protected production boundary", record.size, record.sha256, record.purge_after,
                                               str(destination)))
                continue
            items.append(LifecyclePlanItem(record.source, record.quarantine, LifecycleAction.RESTORE,
                                           "explicit authorization required; verified restore copy; quarantine retained",
                                           record.size, record.sha256, record.purge_after, str(destination)))
        return LifecyclePlan(tuple(items))

    def reconcile(self) -> tuple[LifecycleReconciliation, ...]:
        """Read-only recovery view for interrupted or inconsistent lifecycle state."""
        results: list[LifecycleReconciliation] = []
        for record in self.store.all():
            source = Path(record.source)
            quarantine = Path(record.quarantine)
            source_exists = source.is_file()
            quarantine_exists = quarantine.is_file()
            size_matches: bool | None = None
            sha_matches: bool | None = None
            if quarantine_exists:
                size_matches = quarantine.stat().st_size == record.size
                if size_matches:
                    sha_matches = self._hash(quarantine) == record.sha256
            if not quarantine_exists:
                state, reason = "MISSING_QUARANTINE", "durable record exists but quarantine copy is missing"
            elif not size_matches or not sha_matches:
                state, reason = "CORRUPT_QUARANTINE", "quarantine evidence does not match durable checksum"
            elif record.locked:
                state, reason = "LOCKED_VERIFIED", "quarantine is verified and lifecycle-locked"
            else:
                state, reason = "VERIFIED", "quarantine is present and checksum verified"
            results.append(LifecycleReconciliation(
                record.source, record.quarantine, source_exists, quarantine_exists,
                size_matches, sha_matches, record.locked, state, reason,
            ))
        return tuple(results)


class LifecycleExecutor:
    """Apply only Lab-owned lifecycle actions after explicit authorization."""

    def __init__(self, store: LifecycleStore | None = None, transfer: TransferManager | None = None) -> None:
        self.store = store or LifecycleStore()
        self.transfer = transfer or TransferManager()

    @staticmethod
    def _audit(operation: str, *, source: str | None = None, destination: str | None = None,
               decision: str = "ALLOW", result: str = "SUCCESS", error_code: str | None = None,
               details: dict[str, object] | None = None) -> None:
        conn = open_audit(runtime_paths().root / "audit.db")
        try:
            record_event(conn, event_id=str(uuid.uuid4()), operation=operation,
                         decision=decision, result=result, source=source,
                         destination=destination, error_code=error_code, details=details)
        finally:
            conn.close()

    def quarantine(self, plan: LifecyclePlan, *, authorization_id: str) -> tuple[bool, tuple[str, ...]]:
        results: list[str] = []
        for item in plan.items:
            if item.action is not LifecycleAction.QUARANTINE:
                continue
            receipt = AuthorizationReceipt.for_paths(Operation.TRANSFER, item.source, item.quarantine,
                                                     authorization_id=authorization_id)
            result = self.transfer.transfer(TransferSpec(item.source, item.quarantine), authorization=receipt)
            if not result.success or not result.verified:
                self._audit("QUARANTINE", source=item.source, destination=item.quarantine,
                             result="FAILED", error_code="QUARANTINE_VERIFY")
                return False, tuple(results)
            record = LifecycleRecord(item.source, item.quarantine, item.size,
                                     item.sha256 or result.destination_sha256 or "",
                                     datetime.now(timezone.utc).isoformat(),
                                     item.purge_after or datetime.now(timezone.utc).isoformat())
            self.store.put(record)
            self._audit("QUARANTINE", source=item.source, destination=item.quarantine,
                         details={"sha256": record.sha256, "authorization_id": authorization_id})
            results.append(item.quarantine)
        return True, tuple(results)

    def purge(self, plan: LifecyclePlan, *, authorization_id: str) -> tuple[bool, tuple[str, ...]]:
        removed: list[str] = []
        for item in plan.items:
            if item.action is not LifecycleAction.PURGE_READY:
                continue
            path = Path(item.quarantine).resolve()
            receipt = AuthorizationReceipt.for_paths(Operation.DELETE, path, authorization_id=authorization_id)
            decision = authorize(Operation.DELETE, path, receipt=receipt)
            if not decision.allowed:
                self._audit("PURGE", source=item.source, destination=str(path), decision="DENY",
                             result="BLOCKED", error_code="POLICY_DENIED")
                return False, tuple(removed)
            path.unlink()
            self._audit("PURGE", source=item.source, destination=str(path),
                         details={"authorization_id": authorization_id})
            removed.append(str(path))
        return True, tuple(removed)

    def restore(self, plan: LifecyclePlan, *, authorization_id: str) -> tuple[bool, tuple[str, ...]]:
        restored: list[str] = []
        for item in plan.items:
            if item.action is not LifecycleAction.RESTORE:
                continue
            if not item.destination:
                self._audit("RESTORE", source=item.quarantine, result="FAILED", error_code="MISSING_DESTINATION")
                return False, tuple(restored)
            receipt = AuthorizationReceipt.for_paths(Operation.TRANSFER, item.quarantine, item.destination,
                                                     authorization_id=authorization_id)
            result = self.transfer.transfer(TransferSpec(item.quarantine, item.destination), authorization=receipt)
            if not result.success or not result.verified or result.destination_sha256 != item.sha256:
                self._audit("RESTORE", source=item.quarantine, destination=item.destination,
                             result="FAILED", error_code="RESTORE_VERIFY")
                return False, tuple(restored)
            self._audit("RESTORE", source=item.quarantine, destination=item.destination,
                         details={"sha256": item.sha256, "authorization_id": authorization_id})
            restored.append(item.destination)
        return True, tuple(restored)


def lock_records(store: LifecycleStore, sources: Iterable[str]) -> None:
    for source in sources:
        record = store.get(str(Path(source).resolve()))
        if record is None:
            raise ValueError(f"no lifecycle record for {source}")
        store.set_locked(record.source, True)
