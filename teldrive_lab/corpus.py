"""Automatic, read-only discovery of an existing TelDrive corpus.

R1 deliberately treats TelDrive/rclone as the source of truth.  The Lab owns
only the derived SQLite catalog.  Discovery never writes to the remote, never
hashes/downloads file contents, and reports objects that disappeared since a
previous observation without deleting their catalog records.
"""

from __future__ import annotations

import csv
import io
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

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
class CorpusLimits:
    """Hard bounds for a discovery run."""

    max_entries: int = 100_000
    timeout_seconds: int = 300

    def __post_init__(self) -> None:
        if self.max_entries <= 0:
            raise ValueError("max_entries must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


@dataclass(frozen=True, slots=True)
class CorpusDiscoveryResult:
    remote: str
    root: str
    source_identifier: str
    discovered: int
    skipped: int
    bounded: bool
    stale_paths: tuple[str, ...]
    observed_at: str


class CorpusDiscoveryError(RuntimeError):
    """Base error for corpus discovery failures."""


class DiscoveryLimitError(CorpusDiscoveryError):
    """Raised when a remote exceeds the configured discovery bound."""


class RcloneTelDriveSource:
    """Read-only TelDrive source backed by an existing rclone remote.

    The rclone remote is expected to point at TelDrive.  The adapter uses only
    ``rclone lsf`` (listing) and never invokes copy, move, delete, purge, or
    config mutation commands.
    """

    def __init__(
        self,
        remote: str,
        *,
        root: str = "",
        executable: str = "rclone",
        limits: CorpusLimits | None = None,
    ) -> None:
        self.remote = _validate_remote(remote)
        self.root = root.strip("/")
        self.executable = executable
        self.limits = limits or CorpusLimits()

    @property
    def source_identifier(self) -> str:
        suffix = f"/{self.root}" if self.root else ""
        return f"rclone:teldrive:{self.remote}{suffix}"

    def discover(self, catalog: Catalog) -> CorpusDiscoveryResult:
        candidate = Path(self.root) if self.root else Path(".")
        decision = authorize(Operation.INDEX, candidate)
        if not decision.allowed:
            # The remote is not a production filesystem path, but using the
            # existing operation gate still keeps discovery under one policy.
            # A relative placeholder is always allowed by the R0 safety model.
            raise PermissionError(decision.reason)

        observed_at = utc_now()
        seen: list[str] = []
        discovered = 0
        skipped = 0
        bounded = False

        for row in self._list_rows():
            if discovered >= self.limits.max_entries:
                bounded = True
                break
            try:
                path, size, modified_at = row
                if not path:
                    skipped += 1
                    continue
                normalized = _normalize_remote_path(path)
                if not normalized:
                    skipped += 1
                    continue
                name = Path(normalized).name
                parent = str(Path(normalized).parent)
                if parent == ".":
                    parent = None
                record = FileRecord(
                    path=normalized,
                    name=name,
                    parent_path=parent,
                    size=size,
                    mime_type=None,
                    extension=Path(normalized).suffix.lower() or None,
                    created_at=None,
                    modified_at=modified_at,
                    sha256=None,
                    hash_state=HashState.UNKNOWN,
                    source_type=SourceType.TELDRIVE,
                    source_identifier=self.source_identifier,
                    destination_type=DestinationType.TELDRIVE,
                    destination_identifier=self.remote,
                    telegram_file_id=None,
                    telegram_message_id=None,
                    telegram_channel_id=None,
                    encryption_class=EncryptionClass.UNKNOWN,
                    verification_state=VerificationState.UNVERIFIED,
                    tags=("r1-discovered",),
                    job_id=None,
                    first_seen_at=observed_at,
                    last_seen_at=observed_at,
                )
                catalog.upsert(record)
                seen.append(normalized)
                discovered += 1
            except (TypeError, ValueError):
                skipped += 1

        stale = catalog.reconcile_source(SourceType.TELDRIVE, self.source_identifier, seen)
        return CorpusDiscoveryResult(
            remote=self.remote,
            root=self.root,
            source_identifier=self.source_identifier,
            discovered=discovered,
            skipped=skipped,
            bounded=bounded,
            stale_paths=tuple(record.path for record in stale),
            observed_at=observed_at,
        )

    def _list_rows(self) -> Iterable[tuple[str, int | None, str | None]]:
        target = self.remote if not self.root else f"{self.remote}:{self.root}"
        command = [
            self.executable,
            "lsf",
            target,
            "--recursive",
            "--files-only",
            "--format",
            "pst",
            "--csv",
        ]
        env = os.environ.copy()
        env["RCLONE_ASK_PASSWORD"] = "false"
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
        except OSError as exc:
            raise CorpusDiscoveryError(f"unable to execute rclone: {exc}") from exc

        assert process.stdout is not None
        assert process.stderr is not None
        stderr = ""
        try:
            for line in process.stdout:
                yield _parse_lsf_row(line)
            stderr = process.stderr.read().strip()
        finally:
            process.stdout.close()
            process.stderr.close()

        try:
            return_code = process.wait(timeout=self.limits.timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            process.wait()
            raise CorpusDiscoveryError("rclone discovery timed out") from exc
        if return_code != 0:
            raise CorpusDiscoveryError(stderr or f"rclone exited with status {return_code}")


def discover_teldrive(
    catalog: Catalog,
    *,
    remote: str,
    root: str = "",
    limits: CorpusLimits | None = None,
    executable: str = "rclone",
) -> CorpusDiscoveryResult:
    """Discover an existing TelDrive corpus into the Lab-owned catalog."""
    return RcloneTelDriveSource(remote, root=root, executable=executable, limits=limits).discover(catalog)


def configured_teldrive_remote() -> str | None:
    """Return the explicitly configured TelDrive rclone remote, if present."""
    value = os.environ.get("TELDRIVE_LAB_TELDRIVE_RCLONE_REMOTE", "").strip()
    return value or None


def _validate_remote(remote: str) -> str:
    value = remote.strip()
    if not value or any(char in value for char in "\r\n"):
        raise ValueError("remote must be a non-empty single-line rclone remote")
    if ":" not in value:
        raise ValueError("remote must include an rclone remote name ending with ':'")
    return value.rstrip(":")


def _normalize_remote_path(path: str) -> str:
    value = path.replace("\\", "/").strip("/")
    if not value or value == "." or value.startswith("../") or "/../" in value:
        return ""
    return value


def _parse_lsf_row(line: str) -> tuple[str, int | None, str | None]:
    row = next(csv.reader(io.StringIO(line)))
    if not row:
        return "", None, None
    path = row[0]
    size = None
    modified_at = None
    if len(row) > 1 and row[1]:
        try:
            size = int(row[1])
        except ValueError:
            size = None
    if len(row) > 2 and row[2]:
        try:
            modified_at = datetime.fromisoformat(row[2].replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
        except ValueError:
            modified_at = None
    return path, size, modified_at
