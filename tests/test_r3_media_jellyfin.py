from pathlib import Path

import pytest

from teldrive_lab import media_jellyfin
from teldrive_lab.media_jellyfin import classify_path, discover_filesystem, rclone_mount_command, validate_exposure


def test_media_classification():
    assert classify_path(Path("Movie.mkv")) == ("video", "mkv", 0.99)
    assert classify_path(Path("track.flac")) == ("audio", "flac", 0.99)
    assert classify_path(Path("notes.txt")) is None


def test_discovery_is_bounded_and_non_mutating(tmp_path):
    (tmp_path / "Music").mkdir()
    (tmp_path / "Music" / "a.mp3").write_bytes(b"x")
    found = discover_filesystem(tmp_path, max_depth=3, max_files=10)
    assert len(found) == 1 and found[0].source_path.endswith("a.mp3")


def test_rclone_boundary_is_read_only():
    command = rclone_mount_command("teldrive:root", Path("/tmp/r3-media"))
    assert "--read-only" in command and "--vfs-cache-mode" in command
    assert "copy" not in command and "move" not in command and "delete" not in command


def test_exposure_rejects_protected_overlap(tmp_path):
    protected = tmp_path / "production"
    protected.mkdir()
    try:
        validate_exposure(protected, (protected,))
    except Exception as exc:
        assert "protected" in str(exc)
    else:
        raise AssertionError("protected production root was accepted")


def test_startup_request_retries_transient_503(monkeypatch):
    calls = []

    def fake_request(*args, **kwargs):
        calls.append(1)
        if len(calls) < 3:
            raise media_jellyfin.R3Error("Jellyfin HTTP 503: still starting")
        return 200, {"ok": True}

    sleeps = []
    monkeypatch.setattr(media_jellyfin, "_request", fake_request)
    monkeypatch.setattr(media_jellyfin.time, "sleep", lambda value: sleeps.append(value))

    assert media_jellyfin._startup_request_with_retry("http://127.0.0.1:1234", "/Startup/User") == (200, {"ok": True})
    assert len(calls) == 3
    assert len(sleeps) == 2


def test_startup_request_does_not_retry_non_503(monkeypatch):
    calls = []

    def fake_request(*args, **kwargs):
        calls.append(1)
        raise media_jellyfin.R3Error("Jellyfin HTTP 500: broken")

    monkeypatch.setattr(media_jellyfin, "_request", fake_request)
    with pytest.raises(media_jellyfin.R3Error, match="HTTP 500"):
        media_jellyfin._startup_request_with_retry("http://127.0.0.1:1234", "/Startup/User")
    assert len(calls) == 1


def test_startup_request_honors_deadline(monkeypatch):
    monkeypatch.setattr(media_jellyfin, "_request", lambda *args, **kwargs: (_ for _ in ()).throw(media_jellyfin.R3Error("Jellyfin HTTP 503: still starting")))
    clock = iter([0.0, 0.0, 2.0, 2.0])
    monkeypatch.setattr(media_jellyfin.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(media_jellyfin.time, "sleep", lambda value: None)
    with pytest.raises(media_jellyfin.R3Error, match="HTTP 503"):
        media_jellyfin._startup_request_with_retry("http://127.0.0.1:1234", "/Startup/User", retry_timeout=1)
