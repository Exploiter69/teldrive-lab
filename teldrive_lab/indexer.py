"""Bounded, read-only filesystem indexing for the Lab catalog."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .catalog import Catalog, utc_now
from .models import (
    DestinationType,
    EncryptionClass,
    FileRecord,
    HashState,
    SourceType,
    VerificationState,
)
from .safety import Operation, authorize


@dataclass(frozen=True, slots=True)
class IndexLimits:
    """Hard bounds preventing an accidental unbounded scan."""

    max_entries: int = 10_000
    max_depth: int = 32


@dataclass(frozen=True, slots=True)
class IndexResult:
    root: str
    indexed: int
    skipped: int
    bounded: bool
    seen_paths: tuple[str, ...]


class Indexer:
    """Discover filesystem metadata without opening file contents."""

    def __init__(self, catalog: Catalog, limits: IndexLimits | None = None) -> None:
        self.catalog = catalog
        self.limits = limits or IndexLimits()
        if self.limits.max_entries <= 0:
            raise ValueError("max_entries must be positive")
        if self.limits.max_depth < 0:
            raise ValueError("max_depth must be non-negative")

    def scan(
        self,
        root: str | Path,
        *,
        source_type: SourceType = SourceType.LOCAL,
        source_identifier: str | None = None,
    ) -> IndexResult:
        candidate = Path(root).expanduser()
        decision = authorize(Operation.INDEX, candidate)
        if not decision.allowed:
            raise PermissionError(decision.reason)

        if not candidate.exists() or not candidate.is_dir():
            raise NotADirectoryError(str(candidate))

        root_path = candidate.resolve(strict=True)
        identifier = source_identifier or str(root_path)
        timestamp = utc_now()
        stack: list[tuple[Path, int]] = [(root_path, 0)]
        indexed = 0
        skipped = 0
        seen: list[str] = []
        bounded = False

        while stack:
            directory, depth = stack.pop()
            try:
                entries = os.scandir(directory)
            except OSError:
                skipped += 1
                continue

            with entries:
                for entry in entries:
                    if indexed + skipped >= self.limits.max_entries:
                        bounded = True
                        break

                    try:
                        stat = entry.stat(follow_symlinks=False)
                    except OSError:
                        skipped += 1
                        continue

                    # Symlinks are observed but never followed. They are skipped
                    # until the model has an explicit link/provenance representation.
                    if entry.is_symlink():
                        skipped += 1
                        continue

                    path = Path(entry.path)
                    is_dir = entry.is_dir(follow_symlinks=False)
                    relative_depth = depth + 1
                    if is_dir and relative_depth <= self.limits.max_depth:
                        stack.append((path, relative_depth))

                    created_at = None
                    birthtime = getattr(stat, "st_birthtime", None)
                    if birthtime is not None:
                        from datetime import datetime, timezone

                        created_at = datetime.fromtimestamp(birthtime, timezone.utc).isoformat()

                    record = FileRecord(
                        path=str(path),
                        name=entry.name,
                        parent_path=str(path.parent),
                        size=None if is_dir else stat.st_size,
                        mime_type=None,
                        extension=None if is_dir else path.suffix.lower() or None,
                        created_at=created_at,
                        modified_at=datetime_from_timestamp(stat.st_mtime),
                        sha256=None,
                        hash_state=HashState.UNKNOWN,
                        source_type=source_type,
                        source_identifier=identifier,
                        destination_type=None,
                        destination_identifier=None,
                        telegram_file_id=None,
                        telegram_message_id=None,
                        telegram_channel_id=None,
                        encryption_class=EncryptionClass.UNKNOWN,
                        verification_state=VerificationState.UNVERIFIED,
                        tags=None,
                        job_id=None,
                        first_seen_at=timestamp,
                        last_seen_at=timestamp,
                    )
                    self.catalog.upsert(record)
                    indexed += 1
                    seen.append(str(path))

                if bounded:
                    break

        return IndexResult(
            root=str(root_path),
            indexed=indexed,
            skipped=skipped,
            bounded=bounded,
            seen_paths=tuple(seen),
        )


def datetime_from_timestamp(value: float) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(value, timezone.utc).isoformat()
