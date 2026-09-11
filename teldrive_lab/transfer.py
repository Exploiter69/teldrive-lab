"""Phase 4 transfer-manager foundation.

The transfer manager is deliberately an execution boundary, not a storage
implementation. It plans and performs bounded transfers through approved
backends while preserving the Lab safety contract.
"""

from __future__ import annotations

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
class TransferResult:
    success: bool
    bytes_transferred: int
    source: str
    destination: str
    error: str | None = None


class TransferBackend(Protocol):
    def transfer(self, spec: TransferSpec) -> TransferResult: ...


class LocalCopyBackend:
    """Minimal local backend used for Lab-owned transfers.

    It never bypasses the central safety policy and refuses overwrite unless
    the policy explicitly permits it. Production TelDrive paths remain
    protected by the policy rather than by backend-specific exceptions.
    """

    def transfer(self, spec: TransferSpec) -> TransferResult:
        decision = authorize(
            Operation.OVERWRITE if spec.overwrite else Operation.TRANSFER,
            spec.source,
            spec.destination,
            explicit_authorization=False,
        )
        if not decision.allowed:
            return TransferResult(False, 0, spec.source, spec.destination, decision.reason)

        source = Path(spec.source)
        destination = Path(spec.destination)
        if not source.is_file():
            return TransferResult(False, 0, spec.source, spec.destination, "source is not a regular file")
        if destination.exists() and not spec.overwrite:
            return TransferResult(False, 0, spec.source, spec.destination, "destination exists")

        destination.parent.mkdir(parents=True, exist_ok=True)
        copy2(source, destination)
        return TransferResult(True, source.stat().st_size, spec.source, spec.destination)


class TransferManager:
    def __init__(self, backend: TransferBackend | None = None) -> None:
        self.backend = backend or LocalCopyBackend()

    def transfer(self, spec: TransferSpec) -> TransferResult:
        if spec.kind is not TransferKind.COPY:
            return TransferResult(False, 0, spec.source, spec.destination, "unsupported transfer kind")
        return self.backend.transfer(spec)
