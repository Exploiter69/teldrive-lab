"""Controlled transfer layer for TelDrive Lab.

Transfers are planned separately from execution. Actual mutation requires an
explicit authorization supplied by a higher-level workflow; the transfer
layer never self-authorizes production changes.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from shutil import copy2
from typing import Protocol

from .safety import Operation, authorize


class TransferKind(str, Enum):
    COPY = "COPY"


@dataclass(frozen=True)
class TransferSpec:
    source: str
    destination: str
    kind: TransferKind = TransferKind.COPY
    overwrite: bool = False


@dataclass(frozen=True)
class TransferPlan:
    spec: TransferSpec
    source_exists: bool
    source_size: int | None
    destination_exists: bool
    allowed: bool
    reason: str


@dataclass(frozen=True)
class TransferResult:
    success: bool
    bytes_transferred: int
    source: str
    destination: str
    source_sha256: str | None = None
    destination_sha256: str | None = None
    verified: bool = False
    error: str | None = None


class TransferBackend(Protocol):
    def transfer(self, spec: TransferSpec, *, explicit_authorization: bool = False) -> TransferResult: ...


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


class LocalCopyBackend:
    """Local backend for Lab-owned transfers with post-copy verification."""

    def transfer(self, spec: TransferSpec, *, explicit_authorization: bool = False) -> TransferResult:
        operation = Operation.OVERWRITE if spec.overwrite else Operation.TRANSFER
        decision = authorize(
            operation,
            spec.source,
            spec.destination,
            explicit_authorization=explicit_authorization,
        )
        if not decision.allowed:
            return TransferResult(False, 0, spec.source, spec.destination, error=decision.reason)

        source = Path(spec.source)
        destination = Path(spec.destination)
        if not source.is_file():
            return TransferResult(False, 0, spec.source, spec.destination, error="source is not a regular file")
        if destination.exists() and not spec.overwrite:
            return TransferResult(False, 0, spec.source, spec.destination, error="destination exists")

        source_hash = sha256_file(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        copy2(source, destination)
        destination_hash = sha256_file(destination)
        verified = source_hash == destination_hash
        if not verified:
            return TransferResult(
                False, source.stat().st_size, spec.source, spec.destination,
                source_hash, destination_hash, False, "post-transfer checksum mismatch",
            )
        return TransferResult(
            True, source.stat().st_size, spec.source, spec.destination,
            source_hash, destination_hash, True,
        )


class TransferManager:
    def __init__(self, backend: TransferBackend | None = None) -> None:
        self.backend = backend or LocalCopyBackend()

    def plan(self, spec: TransferSpec) -> TransferPlan:
        source = Path(spec.source)
        destination = Path(spec.destination)
        decision = authorize(
            Operation.OVERWRITE if spec.overwrite else Operation.TRANSFER,
            spec.source,
            spec.destination,
            explicit_authorization=False,
        )
        return TransferPlan(
            spec=spec,
            source_exists=source.is_file(),
            source_size=source.stat().st_size if source.is_file() else None,
            destination_exists=destination.exists(),
            allowed=decision.allowed,
            reason=decision.reason,
        )

    def transfer(self, spec: TransferSpec, *, explicit_authorization: bool = False) -> TransferResult:
        if spec.kind is not TransferKind.COPY:
            return TransferResult(False, 0, spec.source, spec.destination, error="unsupported transfer kind")
        return self.backend.transfer(spec, explicit_authorization=explicit_authorization)
