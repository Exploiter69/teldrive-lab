"""Controlled transfer layer for TelDrive Lab.

Transfers are planned separately from execution. Actual mutation requires an
explicit scope-bound authorization receipt supplied by a higher-level workflow;
the transfer layer never self-authorizes production changes.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from shutil import copystat
from typing import Callable, Protocol

from .concurrency import TransferLimiter
from .safety import AuthorizationReceipt, Operation, authorize


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
class TransferProgress:
    source: str
    destination: str
    bytes_transferred: int
    total_bytes: int


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


ProgressCallback = Callable[[TransferProgress], None]


class TransferBackend(Protocol):
    def transfer(
        self,
        spec: TransferSpec,
        *,
        authorization: AuthorizationReceipt | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> TransferResult: ...


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


class LocalCopyBackend:
    """Local backend using a temporary file plus post-copy SHA-256 verification."""

    def transfer(
        self,
        spec: TransferSpec,
        *,
        authorization: AuthorizationReceipt | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> TransferResult:
        operation = Operation.OVERWRITE if spec.overwrite else Operation.TRANSFER
        decision = authorize(
            operation,
            spec.source,
            spec.destination,
            receipt=authorization,
        )
        if not decision.allowed:
            return TransferResult(False, 0, spec.source, spec.destination, error=decision.reason)

        source = Path(spec.source)
        destination = Path(spec.destination)
        if not source.is_file():
            return TransferResult(False, 0, spec.source, spec.destination, error="source is not a regular file")
        if destination.exists() and not spec.overwrite:
            return TransferResult(False, 0, spec.source, spec.destination, error="destination exists")

        total = source.stat().st_size
        source_hash = sha256_file(source)
        temp_path: Path | None = None
        copied = 0
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=destination.parent, prefix=".teldrive-lab-partial-", delete=False
            ) as temporary:
                temp_path = Path(temporary.name)
                with source.open("rb") as source_handle:
                    while chunk := source_handle.read(1024 * 1024):
                        temporary.write(chunk)
                        copied += len(chunk)
                        if progress_callback is not None:
                            progress_callback(TransferProgress(spec.source, spec.destination, copied, total))
                temporary.flush()
                os.fsync(temporary.fileno())

            destination_hash = sha256_file(temp_path)
            if source_hash != destination_hash:
                return TransferResult(
                    False, copied, spec.source, spec.destination,
                    source_hash, destination_hash, False, "post-transfer checksum mismatch",
                )
            copystat(source, temp_path)
            os.replace(temp_path, destination)
            temp_path = None
            return TransferResult(
                True, copied, spec.source, spec.destination,
                source_hash, destination_hash, True,
            )
        except OSError as exc:
            return TransferResult(False, copied, spec.source, spec.destination,
                                  source_hash, None, False, f"transfer I/O error: {exc}")
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass


class TransferManager:
    def __init__(self, backend: TransferBackend | None = None,
                 limiter: TransferLimiter | None = None) -> None:
        self.backend = backend or LocalCopyBackend()
        self.limiter = limiter

    def plan(self, spec: TransferSpec) -> TransferPlan:
        source = Path(spec.source)
        destination = Path(spec.destination)
        decision = authorize(
            Operation.OVERWRITE if spec.overwrite else Operation.TRANSFER,
            spec.source,
            spec.destination,
        )
        return TransferPlan(
            spec=spec,
            source_exists=source.is_file(),
            source_size=source.stat().st_size if source.is_file() else None,
            destination_exists=destination.exists(),
            allowed=decision.allowed,
            reason=decision.reason,
        )

    def transfer(
        self,
        spec: TransferSpec,
        *,
        authorization: AuthorizationReceipt | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> TransferResult:
        if spec.kind is not TransferKind.COPY:
            return TransferResult(False, 0, spec.source, spec.destination, error="unsupported transfer kind")
        size = 0
        source = Path(spec.source)
        if source.is_file():
            size = source.stat().st_size
        if self.limiter is None:
            return self.backend.transfer(
                spec, authorization=authorization, progress_callback=progress_callback,
            )
        try:
            self.limiter.acquire(size)
        except ValueError as exc:
            return TransferResult(False, 0, spec.source, spec.destination, error=str(exc))
        try:
            return self.backend.transfer(
                spec, authorization=authorization, progress_callback=progress_callback,
            )
        finally:
            self.limiter.release(size)
