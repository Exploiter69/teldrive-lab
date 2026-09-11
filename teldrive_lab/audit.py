"""SQLite-backed audit/event log owned entirely by TelDrive Lab."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    timestamp TEXT NOT NULL,
    operation TEXT NOT NULL,
    job_id TEXT,
    source TEXT,
    destination TEXT,
    decision TEXT NOT NULL,
    result TEXT,
    checksum TEXT,
    error_code TEXT,
    details_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_operation ON events(operation);
CREATE INDEX IF NOT EXISTS idx_events_job_id ON events(job_id);
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def open_audit(path: str | Path) -> sqlite3.Connection:
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def record_event(conn: sqlite3.Connection, *, event_id: str, operation: str,
                 decision: str, result: str | None = None, job_id: str | None = None,
                 source: str | None = None, destination: str | None = None,
                 checksum: str | None = None, error_code: str | None = None,
                 details: dict[str, Any] | None = None) -> None:
    """Persist a non-secret audit event. Callers must redact secrets before this API."""
    conn.execute(
        """INSERT INTO events
        (event_id,timestamp,operation,job_id,source,destination,decision,result,checksum,error_code,details_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (event_id, _utc_now(), operation, job_id, source, destination,
         decision, result, checksum, error_code, json.dumps(details or {}, sort_keys=True)),
    )
    conn.commit()
