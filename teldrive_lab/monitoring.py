"""Read-only monitoring, durable alerts, and local notification records.

Phase 10 deliberately observes the Lab and existing TelDrive installation. It never
repairs, mutates, purges, reorganizes, or reconfigures production resources.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

from .audit import record_event
from .health import Check, system_health


class AlertCode:
    DISK_SPACE_LOW = "DISK_SPACE_LOW"
    DISK_SPACE_CRITICAL = "DISK_SPACE_CRITICAL"
    BACKUP_OVERDUE = "BACKUP_OVERDUE"
    BACKUP_FAILED = "BACKUP_FAILED"
    BACKUP_CORRUPT = "BACKUP_CORRUPT"
    JOB_STUCK = "JOB_STUCK"
    WORKER_UNAVAILABLE = "WORKER_UNAVAILABLE"
    INTEGRITY_FAILURE = "INTEGRITY_FAILURE"
    TELDRIVE_UNHEALTHY = "TELDRIVE_UNHEALTHY"


@dataclass(frozen=True)
class StorageSnapshot:
    path: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    free_percent: float


@dataclass(frozen=True)
class JobSnapshot:
    total: int
    queued: int
    running: int
    verifying: int
    completed: int
    failed: int
    cancelled: int
    paused: int
    stuck: int
    workers: int


@dataclass(frozen=True)
class Alert:
    alert_id: str
    code: str
    severity: str
    message: str
    fingerprint: str
    first_seen: str
    last_seen: str
    active: bool
    occurrences: int
    details: dict[str, object]


@dataclass(frozen=True)
class Notification:
    notification_id: str
    alert_id: str
    channel: str
    created_at: str
    message: str


@dataclass(frozen=True)
class MonitorSnapshot:
    timestamp: str
    health: tuple[Check, ...]
    storage: tuple[StorageSnapshot, ...]
    jobs: JobSnapshot
    alerts: tuple[Alert, ...]


class MonitoringStore:
    """Durable Lab-owned monitoring state. No production state is stored here."""

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id TEXT PRIMARY KEY, code TEXT NOT NULL, severity TEXT NOT NULL,
                message TEXT NOT NULL, fingerprint TEXT NOT NULL UNIQUE,
                first_seen TEXT NOT NULL, last_seen TEXT NOT NULL,
                active INTEGER NOT NULL, occurrences INTEGER NOT NULL,
                details_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts(active, severity, last_seen);
            CREATE TABLE IF NOT EXISTS notifications (
                notification_id TEXT PRIMARY KEY, alert_id TEXT NOT NULL,
                channel TEXT NOT NULL, created_at TEXT NOT NULL, message TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_notifications_alert ON notifications(alert_id, created_at);
            """)

    def upsert_alert(self, *, code: str, severity: str, message: str,
                     fingerprint: str, details: dict[str, object], now: str) -> Alert:
        with sqlite3.connect(self.path) as conn:
            row = conn.execute("SELECT * FROM alerts WHERE fingerprint=?", (fingerprint,)).fetchone()
            if row is None:
                alert_id = uuid.uuid4().hex
                conn.execute("INSERT INTO alerts VALUES (?,?,?,?,?,?,?,?,?,?)",
                             (alert_id, code, severity, message, fingerprint, now, now, 1, 1,
                              json.dumps(details, sort_keys=True)))
            else:
                alert_id = row[0]
                conn.execute("""UPDATE alerts SET severity=?, message=?, last_seen=?, active=1,
                               occurrences=occurrences+1, details_json=? WHERE alert_id=?""",
                             (severity, message, now, json.dumps(details, sort_keys=True), alert_id))
        return self.get(alert_id)

    def resolve_missing(self, active_fingerprints: set[str], now: str) -> None:
        with sqlite3.connect(self.path) as conn:
            if active_fingerprints:
                placeholders = ",".join("?" for _ in active_fingerprints)
                conn.execute(f"UPDATE alerts SET active=0, last_seen=? WHERE active=1 AND fingerprint NOT IN ({placeholders})",
                             (now, *active_fingerprints))
            else:
                conn.execute("UPDATE alerts SET active=0, last_seen=? WHERE active=1", (now,))

    def get(self, alert_id: str) -> Alert:
        with sqlite3.connect(self.path) as conn:
            row = conn.execute("SELECT * FROM alerts WHERE alert_id=?", (alert_id,)).fetchone()
        if row is None:
            raise KeyError(alert_id)
        return self._alert(row)

    def alerts(self, *, active_only: bool = False) -> list[Alert]:
        sql = "SELECT * FROM alerts" + (" WHERE active=1" if active_only else "") + " ORDER BY last_seen DESC, alert_id"
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(sql).fetchall()
        return [self._alert(row) for row in rows]

    def notify(self, alert: Alert, *, channel: str = "local") -> Notification:
        now = _now()
        notification = Notification(uuid.uuid4().hex, alert.alert_id, channel, now, alert.message)
        with sqlite3.connect(self.path) as conn:
            conn.execute("INSERT INTO notifications VALUES (?,?,?,?,?)",
                         (notification.notification_id, notification.alert_id, notification.channel,
                          notification.created_at, notification.message))
        return notification

    @staticmethod
    def _alert(row: sqlite3.Row | tuple) -> Alert:
        return Alert(row[0], row[1], row[2], row[3], row[4], row[5], row[6], bool(row[7]), row[8], json.loads(row[9]))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def storage_snapshot(path: str | Path) -> StorageSnapshot:
    usage = shutil.disk_usage(Path(path).expanduser())
    percent = (usage.free / usage.total * 100.0) if usage.total else 0.0
    return StorageSnapshot(str(Path(path).expanduser()), usage.total, usage.used, usage.free, percent)


def job_snapshot(job_db: str | Path, *, stuck_after_seconds: float = 3600.0) -> JobSnapshot:
    path = Path(job_db).expanduser()
    if not path.exists():
        return JobSnapshot(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    states = {"QUEUED": 0, "RUNNING": 0, "VERIFYING": 0, "COMPLETED": 0, "FAILED": 0, "CANCELLED": 0, "PAUSED": 0}
    now = time.time()
    workers: set[str] = set()
    stuck = 0
    with sqlite3.connect(path) as conn:
        rows = conn.execute("SELECT state,updated,worker_id,lease_until FROM jobs").fetchall()
    for state, updated, worker_id, lease_until in rows:
        states[state] = states.get(state, 0) + 1
        if worker_id:
            workers.add(worker_id)
        if state in {"RUNNING", "VERIFYING"} and updated is not None and now - updated > stuck_after_seconds:
            stuck += 1
    return JobSnapshot(sum(states.values()), states["QUEUED"], states["RUNNING"], states["VERIFYING"],
                       states["COMPLETED"], states["FAILED"], states["CANCELLED"], states["PAUSED"], stuck, len(workers))


def evaluate(*, health: Iterable[Check], storage: Iterable[StorageSnapshot], jobs: JobSnapshot,
             backup_status: dict[str, object] | None = None,
             integrity_failure_count: int = 0,
             low_free_percent: float = 15.0, critical_free_percent: float = 5.0) -> list[tuple[str, str, str, str, dict[str, object]]]:
    """Return deterministic alert tuples without changing any external state."""
    alerts: list[tuple[str, str, str, str, dict[str, object]]] = []
    for item in storage:
        if item.free_percent <= critical_free_percent:
            alerts.append((AlertCode.DISK_SPACE_CRITICAL, "CRITICAL", f"Critical free space on {item.path}: {item.free_percent:.1f}%", f"disk:{item.path}:critical", asdict(item)))
        elif item.free_percent <= low_free_percent:
            alerts.append((AlertCode.DISK_SPACE_LOW, "WARNING", f"Low free space on {item.path}: {item.free_percent:.1f}%", f"disk:{item.path}:low", asdict(item)))
    failed_health = [c.name for c in health if not c.ok]
    if failed_health:
        alerts.append((AlertCode.TELDRIVE_UNHEALTHY, "CRITICAL", "Health checks failed: " + ", ".join(failed_health), "health:" + ",".join(failed_health), {"checks": failed_health}))
    if jobs.stuck:
        alerts.append((AlertCode.JOB_STUCK, "WARNING", f"{jobs.stuck} job(s) appear stuck", "jobs:stuck", {"stuck": jobs.stuck}))
    if jobs.running and jobs.workers == 0:
        alerts.append((AlertCode.WORKER_UNAVAILABLE, "CRITICAL", "Jobs are running but no worker identity is recorded", "workers:unavailable", {"running": jobs.running}))
    if integrity_failure_count:
        alerts.append((AlertCode.INTEGRITY_FAILURE, "CRITICAL", f"{integrity_failure_count} integrity failure(s) reported", "integrity:failure", {"count": integrity_failure_count}))
    if backup_status:
        if backup_status.get("overdue"):
            alerts.append((AlertCode.BACKUP_OVERDUE, "WARNING", "A scheduled backup is overdue", "backup:overdue", backup_status))
        if backup_status.get("failed"):
            alerts.append((AlertCode.BACKUP_FAILED, "CRITICAL", "The latest backup failed", "backup:failed", backup_status))
        if backup_status.get("corrupt"):
            alerts.append((AlertCode.BACKUP_CORRUPT, "CRITICAL", "A backup verification detected corruption or missing data", "backup:corrupt", backup_status))
    return alerts


def collect(*, store: MonitoringStore, audit_path: str | Path, job_db: str | Path,
            storage_paths: Iterable[str | Path], health_probe: Callable[[], list[Check]] = system_health,
            backup_status: dict[str, object] | None = None, integrity_failure_count: int = 0,
            notify: bool = True) -> MonitorSnapshot:
    now = _now()
    health = tuple(health_probe())
    storage = tuple(storage_snapshot(p) for p in storage_paths)
    jobs = job_snapshot(job_db)
    candidates = evaluate(health=health, storage=storage, jobs=jobs, backup_status=backup_status,
                          integrity_failure_count=integrity_failure_count)
    active: set[str] = set()
    alerts: list[Alert] = []
    audit = None
    try:
        audit = sqlite3.connect(Path(audit_path).expanduser()) if Path(audit_path).expanduser().exists() else None
        for code, severity, message, fingerprint, details in candidates:
            active.add(fingerprint)
            alert = store.upsert_alert(code=code, severity=severity, message=message,
                                       fingerprint=fingerprint, details=details, now=now)
            alerts.append(alert)
            if notify:
                store.notify(alert)
            if audit is not None:
                record_event(audit, event_id=uuid.uuid4().hex, operation="MONITOR", decision="ALERT",
                             result=severity, error_code=code, details={"fingerprint": fingerprint})
    finally:
        if audit is not None:
            audit.close()
    store.resolve_missing(active, now)
    alerts = store.alerts(active_only=True)
    return MonitorSnapshot(now, health, storage, jobs, tuple(alerts))


def payload(snapshot: MonitorSnapshot) -> dict[str, object]:
    return {
        "timestamp": snapshot.timestamp,
        "health": [asdict(x) for x in snapshot.health],
        "storage": [asdict(x) for x in snapshot.storage],
        "jobs": asdict(snapshot.jobs),
        "alerts": [asdict(x) for x in snapshot.alerts],
    }


def run_readonly_command(argv: list[str]) -> str:
    """Fixed-argv helper for optional journal/system integration; never mutates state."""
    result = subprocess.run(argv, capture_output=True, text=True, timeout=10, check=False)
    return (result.stdout or result.stderr).strip()
