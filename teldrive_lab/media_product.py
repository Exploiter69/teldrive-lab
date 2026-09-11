"""Stage 5 media-as-data product layer.

Builds on the audited Phase 14 media primitives instead of creating a media
server. All planning/export helpers are deterministic and sidecar/local only.
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .advanced import MEDIA_EXTENSIONS, media_probe, media_records, subtitle_index, thumbnail_capability

SCHEMA = "teldrive-lab.media-library.v1"


@dataclass(frozen=True, slots=True)
class MediaHealth:
    root: str
    media_files: int
    subtitle_files: int
    total_bytes: int
    ffprobe: bool
    ffmpeg: bool
    scan_ms: float


def discover_media(root: Path) -> dict[str, Any]:
    """Return a deterministic media catalog plus subtitle associations."""
    started = time.monotonic()
    media = media_records(root)
    subtitles = subtitle_index(root)
    by_stem: dict[str, list[str]] = {}
    for sub in subtitles:
        by_stem.setdefault(sub["stem"].lower(), []).append(sub["path"])
    for item in media:
        item["subtitles"] = sorted(by_stem.get(Path(item["path"]).stem.lower(), []))
    return {"schema": SCHEMA, "root": str(root), "media": media, "subtitles": subtitles,
            "scan_ms": round((time.monotonic() - started) * 1000, 3)}


def library_export(root: Path, destination: Path) -> dict[str, Any]:
    """Write a stable, rebuildable media metadata export; never moves source data."""
    payload = discover_media(root)
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    payload["catalog_digest"] = hashlib.sha256(canonical.encode()).hexdigest()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"path": str(destination), "schema": SCHEMA, "media": len(payload["media"]),
            "subtitles": len(payload["subtitles"]), "catalog_digest": payload["catalog_digest"]}


def validate_library_export(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    valid = data.get("schema") == SCHEMA and isinstance(data.get("media"), list) and isinstance(data.get("subtitles"), list)
    return {"valid": valid, "schema": data.get("schema"), "media": len(data.get("media", [])),
            "subtitles": len(data.get("subtitles", [])), "catalog_digest": data.get("catalog_digest")}


def cache_materialization_plan(records: Iterable[dict[str, Any]], cache_root: Path, *, max_bytes: int) -> dict[str, Any]:
    """Plan local materialization only; actual provider reads remain transfer jobs."""
    if max_bytes < 0:
        raise ValueError("max_bytes must be non-negative")
    items = []
    used = 0
    for record in records:
        size = int(record.get("size") or 0)
        if size < 0:
            continue
        if used + size > max_bytes:
            continue
        source = str(record.get("path", ""))
        digest = hashlib.sha256(source.encode()).hexdigest()[:16]
        items.append({"source": source, "destination": str(cache_root / digest / Path(source).name),
                      "size": size, "action": "MATERIALIZE_PLAN_ONLY"})
        used += size
    return {"cache_root": str(cache_root), "max_bytes": max_bytes, "planned_bytes": used,
            "items": items, "mutation_performed": False}


def cache_health(cache_root: Path, capacity_bytes: int) -> dict[str, Any]:
    if capacity_bytes < 0:
        raise ValueError("capacity_bytes must be non-negative")
    used = sum(p.stat().st_size for p in cache_root.rglob("*") if p.is_file()) if cache_root.exists() else 0
    ratio = used / capacity_bytes if capacity_bytes else 1.0
    return {"root": str(cache_root), "used_bytes": used, "capacity_bytes": capacity_bytes,
            "ratio": ratio, "state": "critical" if ratio >= .95 else "high" if ratio >= .80 else "normal"}


def media_health(root: Path) -> MediaHealth:
    payload = discover_media(root)
    tools = thumbnail_capability()
    return MediaHealth(str(root), len(payload["media"]), len(payload["subtitles"]),
                       sum(int(x["size"]) for x in payload["media"]), tools["ffprobe"],
                       tools["ffmpeg"], float(payload["scan_ms"]))


def direct_play_guidance(record: dict[str, Any]) -> dict[str, Any]:
    """Advisory organization guidance; never changes a media object."""
    ext = str(record.get("extension", "")).lower()
    mime = str(record.get("mime") or mimetypes.guess_type(str(record.get("name", "")))[0] or "")
    friendly = ext in {".mp4", ".m4a", ".mp3", ".jpg", ".jpeg", ".png", ".webp"}
    return {"path": record.get("path"), "mime": mime, "direct_play_friendly": friendly,
            "reason": "common client-compatible container/codec family" if friendly else "client compatibility varies; inspect technical metadata",
            "action": "GUIDANCE_ONLY"}


def jellyfin_setup_plan(library_root: Path, *, jellyfin_url: str = "http://127.0.0.1:8096") -> dict[str, Any]:
    """Produce operator instructions without mutating Jellyfin or storage."""
    return {
        "provider": "jellyfin", "url": jellyfin_url, "library_root": str(library_root),
        "steps": [
            "create or select a Jellyfin library pointing at the materialized/local media root",
            "keep TelDrive Lab responsible for storage policy, metadata evidence, and verification",
            "let Jellyfin own playback, clients, watch state, subtitles, and transcoding",
            "use read-only metadata integration first; add credentials only at operator runtime",
        ],
        "mutation_performed": False,
        "requires_operator_confirmation": True,
    }


def thumbnail_plan(record: dict[str, Any], destination: Path, *, timestamp_seconds: float = 1.0) -> dict[str, Any]:
    """Return an ffmpeg sidecar command plan; does not execute it."""
    source = Path(str(record["path"]))
    if source.suffix.lower() not in MEDIA_EXTENSIONS:
        raise ValueError("record is not recognized media")
    return {"source": str(source), "destination": str(destination), "timestamp_seconds": timestamp_seconds,
            "tool": "ffmpeg", "command": ["ffmpeg", "-ss", str(timestamp_seconds), "-i", str(source), "-frames:v", "1", str(destination)],
            "action": "SIDECAR_PLAN_ONLY", "production_storage_mutation": False}


def provider_latency_health(provider_health: dict[str, Any] | None = None, *, scan_ms: float | None = None) -> dict[str, Any]:
    """Normalize provider and local media latency without making network calls."""
    result = dict(provider_health or {})
    if scan_ms is not None:
        result["local_scan_ms"] = round(float(scan_ms), 3)
    result.setdefault("state", "UNKNOWN")
    result["measurement_only"] = True
    return result


__all__ = [name for name in globals() if not name.startswith("_")]
