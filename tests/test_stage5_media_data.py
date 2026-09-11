from pathlib import Path

from teldrive_lab.media_product import (
    cache_health,
    cache_materialization_plan,
    direct_play_guidance,
    discover_media,
    jellyfin_setup_plan,
    library_export,
    media_health,
    provider_latency_health,
    thumbnail_plan,
    validate_library_export,
)


def test_discovery_and_subtitle_association(tmp_path):
    movie = tmp_path / "Movie.mkv"
    movie.write_bytes(b"media")
    (tmp_path / "Movie.en.srt").write_text("hello", encoding="utf-8")
    data = discover_media(tmp_path)
    assert len(data["media"]) == 1
    assert data["media"][0]["subtitles"]


def test_stable_library_export_and_validation(tmp_path):
    (tmp_path / "a.mp4").write_bytes(b"a")
    first = tmp_path / "one.json"
    second = tmp_path / "two.json"
    library_export(tmp_path, first)
    library_export(tmp_path, second)
    assert validate_library_export(first)["valid"]
    assert validate_library_export(first)["catalog_digest"] == validate_library_export(second)["catalog_digest"]


def test_materialization_is_plan_only_and_bounded(tmp_path):
    p = tmp_path / "movie.mp4"
    p.write_bytes(b"x" * 10)
    plan = cache_materialization_plan([{"path": str(p), "size": 10}], tmp_path / "cache", max_bytes=10)
    assert plan["planned_bytes"] == 10
    assert plan["mutation_performed"] is False
    assert not (tmp_path / "cache").exists()


def test_cache_health(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "x").write_bytes(b"x" * 8)
    assert cache_health(cache, 10)["state"] == "high"


def test_media_health_and_latency_are_observational(tmp_path):
    (tmp_path / "a.mp3").write_bytes(b"a")
    health = media_health(tmp_path)
    assert health.media_files == 1
    assert provider_latency_health({"state": "HEALTHY"}, scan_ms=health.scan_ms)["measurement_only"]


def test_jellyfin_setup_is_operator_plan_only(tmp_path):
    plan = jellyfin_setup_plan(tmp_path)
    assert plan["provider"] == "jellyfin"
    assert plan["mutation_performed"] is False
    assert plan["requires_operator_confirmation"] is True


def test_direct_play_and_thumbnail_are_advisory(tmp_path):
    p = tmp_path / "movie.mp4"
    p.write_bytes(b"x")
    record = {"path": str(p), "name": p.name, "extension": ".mp4", "mime": "video/mp4"}
    assert direct_play_guidance(record)["action"] == "GUIDANCE_ONLY"
    thumb = thumbnail_plan(record, tmp_path / "poster.jpg")
    assert thumb["action"] == "SIDECAR_PLAN_ONLY"
    assert thumb["production_storage_mutation"] is False
