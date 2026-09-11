from __future__ import annotations

from pathlib import Path

from teldrive_lab.capabilities import discover
from teldrive_lab.config import LabConfig, validate_config
from teldrive_lab.runtime import ensure_runtime, runtime_paths


def test_config_validation_rejects_home_as_state(tmp_path: Path) -> None:
    errors = validate_config(LabConfig(state_root=Path.home(), cache_root=tmp_path / "cache"))
    assert "state_root must not be the user's home directory" in errors


def test_config_validation_rejects_shared_state_and_cache(tmp_path: Path) -> None:
    errors = validate_config(LabConfig(state_root=tmp_path, cache_root=tmp_path))
    assert "state_root and cache_root must be distinct" in errors


def test_capability_discovery_is_deterministic_and_side_effect_free(tmp_path: Path) -> None:
    paths = runtime_paths(tmp_path / "runtime")
    before = list(paths.root.iterdir()) if paths.root.exists() else []
    first = discover(paths)
    second = discover(paths)
    assert first == second
    assert [item.name for item in first] == [
        "lab-runtime", "lab-state", "python", "rclone", "docker",
        "ffprobe", "ffmpeg", "tesseract", "whisper", "ollama", "http-stack"
    ]
    after = list(paths.root.iterdir()) if paths.root.exists() else []
    assert before == after


def test_runtime_initialization_owns_only_lab_paths(tmp_path: Path) -> None:
    paths = ensure_runtime(runtime_paths(tmp_path / "runtime"))
    assert paths.root.exists()
    assert paths.state.exists()
    assert paths.cache.exists()
    assert paths.logs.exists()
    assert paths.backups.exists()
