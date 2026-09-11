"""Deterministic safety boundary for TelDrive Lab.

This module is deliberately dependency-free and side-effect free. It classifies
operations and refuses mutation of the protected TelDrive production boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Operation(str, Enum):
    READ = "read"
    INDEX = "index"
    VERIFY = "verify"
    PLAN = "plan"
    DRY_RUN = "dry-run"
    TRANSFER = "transfer"
    WRITE = "write"
    DELETE = "delete"
    MOVE = "move"
    RENAME = "rename"
    OVERWRITE = "overwrite"
    RECONFIGURE = "reconfigure"


MUTATING = frozenset({
    Operation.TRANSFER,
    Operation.WRITE,
    Operation.DELETE,
    Operation.MOVE,
    Operation.RENAME,
    Operation.OVERWRITE,
    Operation.RECONFIGURE,
})

# Exact production roots from PRODUCTION_BOUNDARY.md. These are intentionally
# explicit rather than inferred from the current machine at runtime.
PROTECTED_ROOTS = tuple(Path(p).expanduser() for p in (
    "~/TelegramRaw",
    "~/TelegramDrive",
    "~/teldrive",
    "~/teldrive-project",
))

PROTECTED_STATE = tuple(Path(p).expanduser() for p in (
    "~/teldrive/session.db",
    "/run/docker.sock",
))


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    requires_authorization: bool = False


def _resolve(path: str | Path) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def is_protected(path: str | Path) -> bool:
    """Return True if *path* is inside a protected production root/state path."""
    candidate = _resolve(path)
    for root in (*PROTECTED_ROOTS, *PROTECTED_STATE):
        root = root.resolve(strict=False)
        if candidate == root or root in candidate.parents:
            return True
    return False


def authorize(operation: Operation, *paths: str | Path, explicit_authorization: bool = False) -> Decision:
    """Make a deterministic, fail-closed policy decision.

    Reads and non-mutating planning operations are allowed. Mutations require
    explicit authorization, and mutations touching protected production paths
    are denied by this foundation regardless of authorization.
    """
    protected = [str(p) for p in paths if is_protected(p)]
    if protected:
        return Decision(False, f"protected production boundary: {', '.join(protected)}")

    if operation in MUTATING and not explicit_authorization:
        return Decision(False, "mutation requires explicit authorization", True)

    return Decision(True, "allowed")
