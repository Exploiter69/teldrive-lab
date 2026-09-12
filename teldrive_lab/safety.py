"""Deterministic safety boundary for TelDrive Lab.

This module is deliberately dependency-free and side-effect free. It classifies
operations and refuses mutation of the protected TelDrive production boundary.
"""

from __future__ import annotations

import os
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


MUTATING = frozenset(
    {
        Operation.TRANSFER,
        Operation.WRITE,
        Operation.DELETE,
        Operation.MOVE,
        Operation.RENAME,
        Operation.OVERWRITE,
        Operation.RECONFIGURE,
    }
)

# TelDrive production paths are fixed host paths, not paths relative to the
# process user's HOME. This keeps the built-in safety boundary identical in
# production, CI, containers, and test environments.
PRODUCTION_HOME = Path("/home/thakuralok")
BUILTIN_PROTECTED_ROOTS = (
    PRODUCTION_HOME / "TelegramRaw",
    PRODUCTION_HOME / "TelegramDrive",
    PRODUCTION_HOME / "teldrive",
    PRODUCTION_HOME / "teldrive-project",
)
BUILTIN_PROTECTED_STATE = (
    PRODUCTION_HOME / "teldrive" / "session.db",
    Path("/run/docker.sock"),
)


def _configured_paths(name: str) -> tuple[Path, ...]:
    """Parse an additive path-list environment variable.

    Empty entries are ignored. Invalid/empty configuration never weakens the
    built-in boundary. Paths are normalized only when evaluated by the safety
    checks, so this helper remains side-effect free.
    """
    raw = os.environ.get(name, "")
    return tuple(Path(item).expanduser() for item in raw.split(os.pathsep) if item.strip())


def protected_roots() -> tuple[Path, ...]:
    """Return built-in plus operator-configured protected roots."""
    return BUILTIN_PROTECTED_ROOTS + _configured_paths("TELDRIVE_LAB_PROTECTED_ROOTS")


def protected_state() -> tuple[Path, ...]:
    """Return built-in plus operator-configured protected state paths."""
    return BUILTIN_PROTECTED_STATE + _configured_paths("TELDRIVE_LAB_PROTECTED_STATE")


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    requires_authorization: bool = False


@dataclass(frozen=True)
class AuthorizationReceipt:
    """Explicit, scope-bound approval issued outside the worker/executor.

    A receipt never permits protected production mutation. It only satisfies the
    explicit-authorization requirement for a non-production mutation whose
    operation and exact normalized paths match this receipt.
    """

    operation: Operation
    paths: tuple[str, ...]
    approved: bool = True
    authorization_id: str = "explicit"

    @classmethod
    def for_paths(
        cls,
        operation: Operation,
        *paths: str | Path,
        authorization_id: str = "explicit",
    ) -> "AuthorizationReceipt":
        if operation not in MUTATING:
            raise ValueError("authorization receipts are only valid for mutations")
        normalized = tuple(sorted(str(_resolve(path)) for path in paths))
        return cls(operation=operation, paths=normalized, authorization_id=authorization_id)


def _resolve(path: str | Path) -> Path:
    """Normalize a path without depending on the executing user's HOME."""
    candidate = Path(path)
    if not candidate.is_absolute():
        text = str(candidate)
        if text == "~" or text.startswith("~/"):
            candidate = PRODUCTION_HOME / text[2:] if text != "~" else PRODUCTION_HOME
        else:
            candidate = Path.cwd() / candidate
    return candidate.resolve(strict=False)


def is_protected(path: str | Path) -> bool:
    """Return True if *path* is inside a protected production root/state path."""
    candidate = _resolve(path)
    for root in (*protected_roots(), *protected_state()):
        root = _resolve(root)
        if candidate == root or root in candidate.parents:
            return True
    return False


def authorize(
    operation: Operation,
    *paths: str | Path,
    explicit_authorization: bool = False,
    receipt: AuthorizationReceipt | None = None,
) -> Decision:
    """Make a deterministic, fail-closed policy decision.

    Read-only operations may inspect protected production paths. Any mutation
    touching a protected path is denied. Non-production mutations require a
    scope-bound receipt when a receipt is supplied; the legacy boolean remains
    accepted for compatibility with the existing Phase 4 local backend.
    """
    protected = [str(p) for p in paths if is_protected(p)]

    if protected and operation in MUTATING:
        return Decision(False, f"protected production boundary: {', '.join(protected)}")

    if operation in MUTATING:
        if receipt is not None:
            requested = tuple(sorted(str(_resolve(path)) for path in paths))
            if not receipt.approved:
                return Decision(False, "authorization receipt is not approved", True)
            if receipt.operation is not operation:
                return Decision(False, "authorization receipt operation mismatch", True)
            if receipt.paths != requested:
                return Decision(False, "authorization receipt scope mismatch", True)
            return Decision(True, f"authorized by receipt {receipt.authorization_id}")
        if not explicit_authorization:
            return Decision(False, "mutation requires explicit authorization", True)

    if protected:
        return Decision(True, f"read-only access to protected production: {', '.join(protected)}")

    return Decision(True, "allowed")
