"""Read-only transfer reconciliation and integrity verification."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .transfer import sha256_file


@dataclass(frozen=True)
class Reconciliation:
    exists: bool
    size: int | None
    sha256: str | None
    matches_size: bool
    matches_sha256: bool
    verified: bool
    reason: str


def reconcile_file(path: str, *, expected_size: int | None = None,
                   expected_sha256: str | None = None) -> Reconciliation:
    """Inspect one local file; never creates, changes, or removes anything."""
    target = Path(path)
    if not target.is_file():
        return Reconciliation(False, None, None, expected_size is None,
                              expected_sha256 is None, False, "file missing")
    size = target.stat().st_size
    size_ok = expected_size is None or size == expected_size
    digest = sha256_file(target) if expected_sha256 is not None else None
    hash_ok = expected_sha256 is None or digest == expected_sha256
    verified = size_ok and hash_ok
    if verified:
        reason = "verified"
    elif not size_ok:
        reason = "size mismatch"
    else:
        reason = "checksum mismatch"
    return Reconciliation(True, size, digest, size_ok, hash_ok, verified, reason)
