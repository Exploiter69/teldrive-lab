"""Safe local configuration validation for TelDrive Lab.

Configuration is intentionally environment-based at this stage. Validation only
reads values and never changes production TelDrive configuration.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LabConfig:
    state_root: Path
    cache_root: Path


def load_config() -> LabConfig:
    state = Path(os.environ.get("TELDRIVE_LAB_STATE", "~/.local/share/teldrive-lab")).expanduser()
    cache = Path(os.environ.get("TELDRIVE_LAB_CACHE", str(state / "cache"))).expanduser()
    return LabConfig(state_root=state, cache_root=cache)


def validate_config(config: LabConfig) -> list[str]:
    """Return validation errors without creating directories or touching providers."""
    errors: list[str] = []
    if config.state_root == Path.home():
        errors.append("state_root must not be the user's home directory")
    if config.cache_root == Path.home():
        errors.append("cache_root must not be the user's home directory")
    if config.state_root == config.cache_root:
        errors.append("state_root and cache_root must be distinct")
    for name, path in (("state_root", config.state_root), ("cache_root", config.cache_root)):
        if path.is_file():
            errors.append(f"{name} points to a file: {path}")
    return errors


def config_report() -> dict[str, object]:
    config = load_config()
    errors = validate_config(config)
    return {
        "valid": not errors,
        "state_root": str(config.state_root),
        "cache_root": str(config.cache_root),
        "errors": errors,
    }
