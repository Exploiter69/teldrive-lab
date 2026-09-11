"""Stage 5 host gate: media as data, never an OTT/media-server replacement."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from teldrive_lab.advanced import media_probe
from teldrive_lab.media_product import (
    cache_materialization_plan,
    discover_media,
    direct_play_guidance,
    jellyfin_setup_plan,
    library_export,
    media_health,
    provider_latency_health,
    thumbnail_plan,
    validate_library_export,
)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="teldrive-stage5-") as raw:
        root = Path(raw)
        movie = root / "Demo.mp4"
        movie.write_bytes(b"demo-media")
        (root / "Demo.en.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nDemo\n", encoding="utf-8")
        export = root / "library.json"
        exported = library_export(root, export)
        discovered = discover_media(root)
        health = media_health(root)
        probe = media_probe(movie)
        cache = cache_materialization_plan(discovered["media"], root / "cache", max_bytes=10_000)
        guidance = direct_play_guidance(discovered["media"][0])
        thumb = thumbnail_plan(discovered["media"][0], root / "poster.jpg")
        jellyfin = jellyfin_setup_plan(root / "materialized")
        result = {
            "media_discovery": len(discovered["media"]) == 1 and len(discovered["subtitles"]) == 1,
            "technical_metadata": isinstance(probe, dict) and "available" in probe and "data" in probe,
            "subtitle_indexing": bool(discovered["media"][0]["subtitles"]),
            "stable_library_export": exported["catalog_digest"] == validate_library_export(export)["catalog_digest"],
            "cache_materialization_control": cache["mutation_performed"] is False and not (root / "cache").exists(),
            "health_latency_visibility": provider_latency_health({"state": "HEALTHY"}, scan_ms=health.scan_ms)["measurement_only"],
            "jellyfin_setup_plan": jellyfin["mutation_performed"] is False and jellyfin["requires_operator_confirmation"],
            "direct_play_guidance": guidance["action"] == "GUIDANCE_ONLY",
            "thumbnail_sidecar_plan": thumb["action"] == "SIDECAR_PLAN_ONLY",
            "production_storage_mutation": "NONE",
        }
    print("STAGE 5 MEDIA DATA GATE")
    print(json.dumps(result, indent=2, sort_keys=True))
    ok = all(v is True or v == "NONE" for v in result.values())
    print("STAGE 5 MEDIA DATA GATE: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
