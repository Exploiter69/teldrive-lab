"""Deterministic capability discovery for TelDrive Lab productization.

This module is observational only. It never starts services, changes configuration,
accesses Telegram data, or mutates production storage.
"""
from __future__ import annotations

import importlib.util
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

from .runtime import RuntimePaths


@dataclass(frozen=True)
class Capability:
    name: str
    available: bool
    kind: str
    detail: str


def _command(name: str, executable: str, *, kind: str = "optional-provider") -> Capability:
    path = shutil.which(executable)
    return Capability(name, path is not None, kind, f"executable={path}" if path else "executable=unavailable")


def discover(paths: RuntimePaths) -> list[Capability]:
    """Return a stable, side-effect-free capability inventory."""
    return [
        Capability("lab-runtime", paths.root.exists(), "core", f"root={paths.root}"),
        Capability("lab-state", paths.state.exists(), "core", f"state={paths.state}"),
        Capability("python", True, "core", "python runtime available"),
        _command("rclone", "rclone"),
        _command("docker", "docker"),
        _command("ffprobe", "ffprobe"),
        _command("ffmpeg", "ffmpeg"),
        _command("tesseract", "tesseract"),
        _command("whisper", "whisper"),
        Capability("ollama", shutil.which("ollama") is not None, "optional-ai", "executable=available" if shutil.which("ollama") else "executable=unavailable"),
        Capability("http-stack", importlib.util.find_spec("http") is not None, "core", "python standard library"),
    ]


def capability_dict(paths: RuntimePaths) -> list[dict[str, object]]:
    return [asdict(item) for item in discover(paths)]
