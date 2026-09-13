"""Runtime-state layout; never reuses TelDrive production state."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .safety import is_protected


@dataclass(frozen=True)
class RuntimePaths:
    root: Path
    state: Path
    cache: Path
    logs: Path
    backups: Path


def _validate_lab_path(path: Path, label: str) -> Path:
    """Reject Lab-owned state/cache configured inside protected production."""
    resolved = path.resolve(strict=False)
    if is_protected(resolved):
        raise ValueError(f"{label} resolves inside a protected production boundary: {resolved}")
    return resolved


def runtime_paths(root: str | Path | None = None) -> RuntimePaths:
    base = Path(root).expanduser() if root else Path(
        os.environ.get("TELDRIVE_LAB_STATE", "~/.local/share/teldrive-lab")
    ).expanduser()
    cache_env = os.environ.get("TELDRIVE_LAB_CACHE")
    cache = Path(cache_env).expanduser() if cache_env else base / "cache"

    base = _validate_lab_path(base, "TELDRIVE_LAB_STATE")
    cache = _validate_lab_path(cache, "TELDRIVE_LAB_CACHE")
    # A cache outside the configured state root is valid, but every Lab-owned
    # path must independently remain outside the protected boundary.
    return RuntimePaths(
        root=base,
        state=base / "state",
        cache=cache,
        logs=base / "logs",
        backups=base / "backups",
    )


def ensure_runtime(paths: RuntimePaths | None = None) -> RuntimePaths:
    """Create only Lab-owned runtime directories."""
    paths = paths or runtime_paths()
    for directory in (paths.root, paths.state, paths.cache, paths.logs, paths.backups):
        if is_protected(directory):
            raise ValueError(f"runtime path is protected production state: {directory}")
        directory.mkdir(parents=True, exist_ok=True)
    return paths
