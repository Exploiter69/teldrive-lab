"""Optional local media/document providers used by Phases 14-15.

Providers write only to caller-selected Lab-owned destinations and use local tools.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path
from typing import Any


def generate_thumbnail(source: Path, destination: Path, *, timestamp: str = "00:00:05", timeout: int = 60) -> dict[str, Any]:
    """Generate a sidecar thumbnail with ffmpeg; never writes beside production source."""
    if shutil.which("ffmpeg") is None:
        return {"available": False, "generated": False, "reason": "ffmpeg_not_installed"}
    destination.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", timestamp, "-i", str(source),
         "-frames:v", "1", "-vf", "scale=640:-1", "-y", str(destination)],
        capture_output=True, text=True, timeout=timeout, check=False,
    )
    return {"available": True, "generated": proc.returncode == 0 and destination.is_file(),
            "destination": str(destination), "stderr": proc.stderr[-1000:]}


def classify_document(path: Path) -> dict[str, Any]:
    ext=path.suffix.lower()
    if ext in {".pdf"}: category="document/pdf"
    elif ext in {".md",".txt",".rst",".log"}: category="document/text"
    elif ext in {".csv",".tsv",".json",".yaml",".yml"}: category="dataset/structured"
    elif ext in {".py",".js",".ts",".go",".rs",".java",".c",".cpp",".h"}: category="source/code"
    elif ext in {".mp4",".mkv",".webm",".mov",".avi"}: category="media/video"
    elif ext in {".mp3",".flac",".wav",".m4a",".ogg",".opus"}: category="media/audio"
    elif ext in {".jpg",".jpeg",".png",".webp",".gif"}: category="media/image"
    else: category="unknown"
    return {"path":str(path),"category":category,"confidence":1.0 if category!="unknown" else 0.0,"authoritative":False}


def vision_model_capability() -> dict[str, Any]:
    """Advertise local-only vision providers without requiring one."""
    return {"ollama": bool(shutil.which("ollama")), "llama_cpp": bool(shutil.which("llama-cli")), "remote": False,
            "writes_production": False, "authority": "advisory"}


def perceptual_fingerprint(path: Path, sample_bytes: int = 1_048_576) -> str:
    """Dependency-free stable content fingerprint useful for local visual grouping."""
    with path.open("rb") as f: data=f.read(sample_bytes)
    return hashlib.sha256(data).hexdigest()
