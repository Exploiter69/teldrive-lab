"""Non-destructive integrity verification and duplicate intelligence.

Phase 7 treats checksums and duplicate groups as evidence, never as authority
for destructive actions. The module owns only Lab runtime state and performs
read-only inspection of source files.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Iterable

from .models import FileRecord, VerificationState
from .runtime import runtime_paths

SCHEMA_VERSION = 1


class IntegrityState(StrEnum):
    VERIFIED = "VERIFIED"
    MISSING = "MISSING"
    CHANGED = "CHANGED"
    MISMATCH = "MISMATCH"
    UNVERIFIABLE = "UNVERIFIABLE"


@dataclass(frozen=True, slots=True)
class ChecksumEvidence:
    path: str
    size: int
    sha256: str
    modified_ns: int
    computed_at: str
    state: IntegrityState


@dataclass(frozen=True, slots=True)
class IntegrityResult:
    path: str
    expected_sha256: str | None
    actual_sha256: str | None
    expected_size: int | None
    actual_size: int | None
    state: IntegrityState

    @property
    def verified(self) -> bool:
        return self.state is IntegrityState.VERIFIED


@dataclass(frozen=True, slots=True)
class DuplicateGroup:
    size: int
    sha256: str
    paths: tuple[str, ...]

    @property
    def reclaimable_bytes(self) -> int:
        return max(0, len(self.paths) - 1) * self.size


@dataclass(frozen=True, slots=True)
class IntegrityReport:
    results: tuple[IntegrityResult, ...]

    @property
    def verified(self) -> int:
        return sum(item.verified for item in self.results)

    @property
    def missing(self) -> int:
        return sum(item.state is IntegrityState.MISSING for item in self.results)

    @property
    def changed(self) -> int:
        return sum(item.state is IntegrityState.CHANGED for item in self.results)

    @property
    def mismatched(self) -> int:
        return sum(item.state is IntegrityState.MISMATCH for item in self.results)

    @property
    def unverifiable(self) -> int:
        return sum(item.state is IntegrityState.UNVERIFIABLE for item in self.results)


class IntegrityStore:
    """Lab-owned checksum evidence database; never production state."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else runtime_paths().root / "integrity.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS checksums (
                    path TEXT PRIMARY KEY,
                    size INTEGER NOT NULL,
                    sha256 TEXT NOT NULL,
                    modified_ns INTEGER NOT NULL,
                    computed_at TEXT NOT NULL,
                    state TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_checksums_sha_size ON checksums(sha256, size);
                """
            )
            row = db.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
            if row is None:
                db.execute("INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,))
            elif row["version"] != SCHEMA_VERSION:
                raise RuntimeError(f"unsupported integrity schema {row['version']}")
            db.commit()

    def record(self, evidence: ChecksumEvidence) -> None:
        with self._connect() as db:
            db.execute(
                """INSERT INTO checksums(path,size,sha256,modified_ns,computed_at,state)
                   VALUES(?,?,?,?,?,?)
                   ON CONFLICT(path) DO UPDATE SET size=excluded.size,
                   sha256=excluded.sha256, modified_ns=excluded.modified_ns,
                   computed_at=excluded.computed_at, state=excluded.state""",
                (evidence.path, evidence.size, evidence.sha256, evidence.modified_ns,
                 evidence.computed_at, evidence.state.value),
            )
            db.commit()

    def get(self, path: str) -> ChecksumEvidence | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM checksums WHERE path=?", (path,)).fetchone()
            if row is None:
                return None
            return ChecksumEvidence(row["path"], row["size"], row["sha256"],
                                    row["modified_ns"], row["computed_at"], IntegrityState(row["state"]))


def sha256_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def verify_path(path: str | Path, *, expected_sha256: str | None = None,
                expected_size: int | None = None) -> IntegrityResult:
    target = Path(path)
    if not target.is_file():
        return IntegrityResult(str(target), expected_sha256, None, expected_size, None,
                               IntegrityState.MISSING)
    try:
        stat = target.stat()
        actual_size = stat.st_size
        if expected_size is not None and actual_size != expected_size:
            actual_hash = sha256_file(target)
            return IntegrityResult(str(target), expected_sha256, actual_hash, expected_size,
                                   actual_size, IntegrityState.CHANGED)
        actual_hash = sha256_file(target)
        if expected_sha256 and actual_hash != expected_sha256:
            return IntegrityResult(str(target), expected_sha256, actual_hash, expected_size,
                                   actual_size, IntegrityState.MISMATCH)
        return IntegrityResult(str(target), expected_sha256, actual_hash, expected_size,
                               actual_size, IntegrityState.VERIFIED)
    except OSError:
        return IntegrityResult(str(target), expected_sha256, None, expected_size, None,
                               IntegrityState.UNVERIFIABLE)


def verify_records(records: Iterable[FileRecord], *, store: IntegrityStore | None = None) -> IntegrityReport:
    """Verify catalog-backed files without modifying the source or catalog."""
    results: list[IntegrityResult] = []
    for record in sorted(records, key=lambda item: (item.path, item.name, item.id or 0)):
        result = verify_path(record.path, expected_sha256=record.sha256, expected_size=record.size)
        results.append(result)
        if store and result.actual_sha256 is not None:
            stat = Path(record.path).stat()
            store.record(ChecksumEvidence(
                path=record.path,
                size=stat.st_size,
                sha256=result.actual_sha256,
                modified_ns=stat.st_mtime_ns,
                computed_at=datetime.now(timezone.utc).isoformat(),
                state=result.state,
            ))
    return IntegrityReport(tuple(results))


def duplicate_groups(records: Iterable[FileRecord]) -> tuple[DuplicateGroup, ...]:
    """Group known hashes by (size, SHA-256); never delete or merge anything."""
    groups: dict[tuple[int, str], list[str]] = {}
    for record in records:
        if record.sha256 and record.size is not None and record.size >= 0:
            groups.setdefault((record.size, record.sha256), []).append(record.path)
    result = [DuplicateGroup(size, digest, tuple(sorted(set(paths))))
              for (size, digest), paths in groups.items() if len(set(paths)) > 1]
    return tuple(sorted(result, key=lambda group: (group.size, group.sha256, group.paths)))


def missing_verified_copies(records: Iterable[FileRecord]) -> tuple[str, ...]:
    """Report catalog entries marked VERIFIED whose observed path disappeared."""
    missing: list[str] = []
    for record in records:
        if record.verification_state is VerificationState.VERIFIED and not Path(record.path).is_file():
            missing.append(record.path)
    return tuple(sorted(missing))


def stale_checksum_paths(records: Iterable[FileRecord], store: IntegrityStore) -> tuple[str, ...]:
    """Report checksum evidence whose stored size/mtime no longer matches the file."""
    stale: list[str] = []
    for record in records:
        evidence = store.get(record.path)
        target = Path(record.path)
        if evidence is None or not target.is_file():
            continue
        stat = target.stat()
        if evidence.size != stat.st_size or evidence.modified_ns != stat.st_mtime_ns:
            stale.append(record.path)
    return tuple(sorted(stale))


def benchmark_hash_algorithms(path: str | Path, *, iterations: int = 1) -> dict[str, object]:
    """Benchmark SHA-256 and optionally BLAKE3 when already installed.

    BLAKE3 is strictly optional: Phase 7 never installs a dependency or changes
    the canonical checksum algorithm based on a benchmark.
    """
    target = Path(path)
    results: dict[str, object] = {"path": str(target), "bytes": target.stat().st_size}
    start = time.perf_counter()
    digest = ""
    for _ in range(iterations):
        digest = sha256_file(target)
    results["sha256_seconds"] = round(time.perf_counter() - start, 6)
    results["sha256"] = digest
    try:
        import blake3  # type: ignore
    except ImportError:
        results["blake3"] = "unavailable"
        return results
    start = time.perf_counter()
    for _ in range(iterations):
        hasher = blake3.blake3()
        with target.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                hasher.update(chunk)
        blake_digest = hasher.hexdigest()
    results["blake3_seconds"] = round(time.perf_counter() - start, 6)
    results["blake3"] = blake_digest
    return results


def duplicate_payload(groups: Iterable[DuplicateGroup]) -> list[dict[str, object]]:
    return [
        {"size": group.size, "sha256": group.sha256, "paths": list(group.paths),
         "copies": len(group.paths), "reclaimable_bytes": group.reclaimable_bytes}
        for group in groups
    ]
