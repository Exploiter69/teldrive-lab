"""Read-only health probes for the existing TelDrive foundation."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from .safety import is_protected


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


def path_check(name: str, path: str | Path) -> Check:
    p = Path(path).expanduser()
    if not is_protected(p):
        return Check(name, False, "refusing health probe outside declared production boundary")
    return Check(name, p.exists() and os.access(p, os.R_OK), f"exists={p.exists()} readable={os.access(p, os.R_OK)}")


def command_check(name: str, argv: list[str]) -> Check:
    """Execute a fixed, read-only command; callers must supply a trusted argv."""
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return Check(name, False, str(exc))
    detail = (result.stdout or result.stderr).strip().splitlines()[0:3]
    return Check(name, result.returncode == 0, "\\n".join(detail) or f"exit={result.returncode}")


def system_health() -> list[Check]:
    checks = [
        path_check("TelegramRaw", "~/TelegramRaw"),
        path_check("TelegramDrive", "~/TelegramDrive"),
        command_check("docker", ["docker", "info", "--format", "{{.ServerVersion}}"]),
        command_check("rclone", ["rclone", "version"]),
        Check("disk", shutil.disk_usage(Path.home()).free > 0, f"free_bytes={shutil.disk_usage(Path.home()).free}"),
    ]
    return checks


def health_dict() -> list[dict[str, object]]:
    return [asdict(check) for check in system_health()]
