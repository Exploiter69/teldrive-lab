"""Runtime-state layout; never reuses TelDrive production state."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimePaths:
    root: Path
    state: Path
    cache: Path
    logs: Path
    backups: Path


def runtime_paths(root: str | Path | None = None) -> RuntimePaths:
    base = Path(root).expanduser() if root else Path(
        os.environ.get("TELDRIVE_LAB_STATE", "~/.local/share/teldrive-lab")
    ).expanduser()
    return RuntimePaths(
        root=base,
        state=base / "state",
        cache=Path(os.environ.get("TELDRIVE_LAB_CACHE", "~/.cache/teldrive-lab")).expanduser(),
        logs=base / "logs",
        backups=base / "backups",
    )


def ensure_runtime(paths: RuntimePaths | None = None) -> RuntimePaths:
    """Create only Lab-owned runtime directories."""
    paths = paths or runtime_paths()
    for directory in (paths.root, paths.state, paths.cache, paths.logs, paths.backups):
        directory.mkdir(parents=True, exist_ok=True)
    return paths
