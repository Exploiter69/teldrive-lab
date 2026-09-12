from pathlib import Path

import pytest

from teldrive_lab.advanced import CASStore, dedup_plan, image_vision_summary, manifest_tree
from teldrive_lab.resources import ResourceLimitError, iter_files, stream_sha256


def test_iter_files_is_deterministic_and_bounded(tmp_path: Path):
    (tmp_path / "b.txt").write_text("b")
    (tmp_path / "a.txt").write_text("a")
    nested = tmp_path / "nested"; nested.mkdir(); (nested / "c.txt").write_text("c")
    assert [p.name for p in iter_files(tmp_path)] == ["a.txt", "b.txt", "c.txt"]
    with pytest.raises(ResourceLimitError): list(iter_files(tmp_path, max_files=2))
    with pytest.raises(ResourceLimitError): list(iter_files(tmp_path, max_depth=0))


def test_symlink_does_not_escape_root(tmp_path: Path):
    outside = tmp_path.parent / "r0-outside.txt"; outside.write_text("outside")
    try:
        (tmp_path / "escape.txt").symlink_to(outside)
    except OSError:
        pytest.skip("symlinks unavailable")
    assert all(p.name != "escape.txt" for p in iter_files(tmp_path))


def test_stream_hash_and_bounded_sample(tmp_path: Path):
    p = tmp_path / "large.bin"; p.write_bytes(b"x" * 3_000_000)
    digest, size = stream_sha256(p)
    import hashlib
    assert digest == hashlib.sha256(b"x" * 3_000_000).hexdigest()
    assert size == 3_000_000
    result = image_vision_summary(p, max_bytes=1234)
    assert result["bytes_sampled"] == 1234


def test_cas_and_dedup_stream_paths(tmp_path: Path):
    a = tmp_path / "a.bin"; b = tmp_path / "b.bin"; a.write_bytes(b"same" * 10000); b.write_bytes(a.read_bytes())
    digest = CASStore(tmp_path / "cas").put(a)
    assert CASStore(tmp_path / "cas").has(digest)
    report = dedup_plan([a, b])
    assert len(report) == 1 and report[0]["reclaimable_bytes"] == a.stat().st_size


def test_manifest_uses_bounded_streaming_hash(tmp_path: Path):
    (tmp_path / "a").write_bytes(b"hello")
    manifest = manifest_tree(tmp_path, max_files=1)
    assert manifest["a"]["size"] == 5
