"""Local, rebuildable SQLite metadata catalog for TelDrive Lab."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Sequence

from .models import (
    DestinationType,
    EncryptionClass,
    FileRecord,
    HashState,
    SourceType,
    VerificationState,
)
from .runtime import ensure_runtime, runtime_paths

SCHEMA_VERSION = 1

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL, name TEXT NOT NULL, parent_path TEXT, size INTEGER,
    mime_type TEXT, extension TEXT, created_at TEXT, modified_at TEXT,
    sha256 TEXT, hash_state TEXT NOT NULL, source_type TEXT NOT NULL,
    source_identifier TEXT NOT NULL, destination_type TEXT,
    destination_identifier TEXT, telegram_file_id TEXT, telegram_message_id TEXT,
    telegram_channel_id TEXT, encryption_class TEXT NOT NULL,
    verification_state TEXT NOT NULL, tags TEXT, job_id TEXT,
    first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL,
    UNIQUE(source_type, source_identifier, path)
);
CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);
CREATE INDEX IF NOT EXISTS idx_files_name ON files(name);
CREATE INDEX IF NOT EXISTS idx_files_parent_path ON files(parent_path);
CREATE INDEX IF NOT EXISTS idx_files_sha256 ON files(sha256);
CREATE INDEX IF NOT EXISTS idx_files_mime_type ON files(mime_type);
CREATE INDEX IF NOT EXISTS idx_files_size ON files(size);
CREATE INDEX IF NOT EXISTS idx_files_created_at ON files(created_at);
CREATE INDEX IF NOT EXISTS idx_files_modified_at ON files(modified_at);
CREATE INDEX IF NOT EXISTS idx_files_source ON files(source_type, source_identifier);
CREATE INDEX IF NOT EXISTS idx_files_destination ON files(destination_type, destination_identifier);
CREATE INDEX IF NOT EXISTS idx_files_verification ON files(verification_state);
CREATE INDEX IF NOT EXISTS idx_files_job ON files(job_id);
"""


class CatalogError(RuntimeError):
    """Base error for catalog failures."""


class SchemaVersionError(CatalogError):
    """Raised when the database schema cannot be safely understood."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tags_json(tags: tuple[str, ...] | None) -> str | None:
    return json.dumps(list(tags), ensure_ascii=False, separators=(",", ":")) if tags is not None else None


class Catalog:
    """Owns only the Lab catalog database, never production state."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path).expanduser() if path else runtime_paths().root / "catalog.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN")
            try:
                connection.executescript(_SCHEMA_SQL)
                row = connection.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
                if row is None:
                    connection.execute("INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,))
                elif row["version"] != SCHEMA_VERSION:
                    raise SchemaVersionError(f"unsupported catalog schema {row['version']}; expected {SCHEMA_VERSION}")
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def schema_version(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
            if row is None:
                raise SchemaVersionError("catalog has no schema version")
            return int(row["version"])

    def upsert(self, record: FileRecord) -> FileRecord:
        identity = (record.source_type.value, record.source_identifier, record.path)
        with self._connect() as connection:
            existing = connection.execute("SELECT id, first_seen_at FROM files WHERE source_type = ? AND source_identifier = ? AND path = ?", identity).fetchone()
            first_seen = existing["first_seen_at"] if existing else record.first_seen_at
            connection.execute(
                """INSERT INTO files (path,name,parent_path,size,mime_type,extension,created_at,modified_at,sha256,hash_state,source_type,source_identifier,destination_type,destination_identifier,telegram_file_id,telegram_message_id,telegram_channel_id,encryption_class,verification_state,tags,job_id,first_seen_at,last_seen_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(source_type,source_identifier,path) DO UPDATE SET
                name=excluded.name,parent_path=excluded.parent_path,size=excluded.size,mime_type=excluded.mime_type,extension=excluded.extension,created_at=excluded.created_at,modified_at=excluded.modified_at,sha256=excluded.sha256,hash_state=excluded.hash_state,destination_type=excluded.destination_type,destination_identifier=excluded.destination_identifier,telegram_file_id=excluded.telegram_file_id,telegram_message_id=excluded.telegram_message_id,telegram_channel_id=excluded.telegram_channel_id,encryption_class=excluded.encryption_class,verification_state=excluded.verification_state,tags=excluded.tags,job_id=excluded.job_id,last_seen_at=excluded.last_seen_at""",
                (record.path, record.name, record.parent_path, record.size, record.mime_type, record.extension, record.created_at, record.modified_at, record.sha256, record.hash_state.value, record.source_type.value, record.source_identifier, record.destination_type.value if record.destination_type else None, record.destination_identifier, record.telegram_file_id, record.telegram_message_id, record.telegram_channel_id, record.encryption_class.value, record.verification_state.value, _tags_json(record.tags), record.job_id, first_seen, record.last_seen_at),
            )
            row = connection.execute("SELECT * FROM files WHERE source_type = ? AND source_identifier = ? AND path = ?", identity).fetchone()
            connection.commit()
            assert row is not None
            return FileRecord.from_mapping(row)

    def get(self, source_type: SourceType, source_identifier: str, path: str) -> FileRecord | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM files WHERE source_type = ? AND source_identifier = ? AND path = ?", (source_type.value, source_identifier, path)).fetchone()
            return FileRecord.from_mapping(row) if row else None

    def count(self) -> int:
        with self._connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM files").fetchone()[0])

    def list_source(self, source_type: SourceType, source_identifier: str) -> list[FileRecord]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM files WHERE source_type = ? AND source_identifier = ? ORDER BY path", (source_type.value, source_identifier)).fetchall()
            return [FileRecord.from_mapping(row) for row in rows]

    def search(self, query: str, *, limit: int = 50) -> list[FileRecord]:
        """Read-only substring search over indexed path/name metadata."""
        query = query.strip()
        if not query:
            raise ValueError("query must not be empty")
        if limit < 1 or limit > 500:
            raise ValueError("limit must be between 1 and 500")
        pattern = f"%{query}%"
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM files WHERE path LIKE ? OR name LIKE ? ORDER BY path LIMIT ?",
                (pattern, pattern, limit),
            ).fetchall()
            return [FileRecord.from_mapping(row) for row in rows]

    def reconcile_source(self, source_type: SourceType, source_identifier: str, seen_paths: Sequence[str]) -> list[FileRecord]:
        seen = set(seen_paths)
        records = self.list_source(source_type, source_identifier)
        return [record for record in records if record.path not in seen]

    def rebuild(self) -> None:
        with self._connect() as connection:
            connection.execute("DROP TABLE IF EXISTS files")
            connection.execute("DROP TABLE IF EXISTS schema_version")
            connection.executescript(_SCHEMA_SQL)
            connection.execute("INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,))
            connection.commit()

    def close(self) -> None:
        return None


def open_default_catalog() -> Catalog:
    paths = ensure_runtime()
    return Catalog(paths.root / "catalog.db")
