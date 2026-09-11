from __future__ import annotations

import subprocess

import pytest

from teldrive_lab.concurrency import TransferLimiter, TransferLimits
from teldrive_lab.reconcile import reconcile_file
from teldrive_lab.retry import RetryClass, RetryPolicy, classify_transfer_error
from teldrive_lab.rclone import RcloneAdapter
from teldrive_lab.safety import AuthorizationReceipt, Operation
from teldrive_lab.transfer import TransferManager, TransferProgress, TransferSpec


def receipt(source, destination):
    return AuthorizationReceipt.for_paths(Operation.TRANSFER, source, destination)


def test_transfer_uses_atomic_verified_copy_and_progress(tmp_path):
    source = tmp_path / "source.bin"
    destination = tmp_path / "nested" / "dest.bin"
    source.write_bytes(b"x" * 4097)
    seen: list[TransferProgress] = []

    result = TransferManager().transfer(
        TransferSpec(str(source), str(destination)),
        authorization=receipt(source, destination),
        progress_callback=seen.append,
    )

    assert result.success is True
    assert result.verified is True
    assert result.source_sha256 == result.destination_sha256
    assert destination.read_bytes() == source.read_bytes()
    assert seen[-1].bytes_transferred == source.stat().st_size
    assert seen[-1].total_bytes == source.stat().st_size
    assert not list(destination.parent.glob(".teldrive-lab-partial-*"))


def test_transfer_does_not_overwrite_without_overwrite_flag(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "dest"
    source.write_text("new")
    destination.write_text("old")

    result = TransferManager().transfer(
        TransferSpec(str(source), str(destination)),
        authorization=receipt(source, destination),
    )

    assert result.success is False
    assert result.error == "destination exists"
    assert destination.read_text() == "old"


def test_reconciliation_is_read_only(tmp_path):
    path = tmp_path / "file"
    path.write_bytes(b"abc")
    import hashlib
    digest = hashlib.sha256(b"abc").hexdigest()

    result = reconcile_file(str(path), expected_size=3, expected_sha256=digest)
    assert result.verified is True
    assert result.reason == "verified"

    bad = reconcile_file(str(path), expected_size=4, expected_sha256=digest)
    assert bad.verified is False
    assert bad.reason == "size mismatch"


def test_limiter_rejects_oversized_transfer():
    limiter = TransferLimiter(TransferLimits(max_workers=1, max_inflight_bytes=10))
    with pytest.raises(ValueError, match="exceeds"):
        limiter.acquire(11)
    assert limiter.inflight_bytes == 0


def test_limiter_tracks_inflight_bytes():
    limiter = TransferLimiter(TransferLimits(max_workers=1, max_inflight_bytes=10))
    limiter.acquire(7)
    assert limiter.inflight_bytes == 7
    limiter.release(7)
    assert limiter.inflight_bytes == 0


def test_retry_policy_is_bounded_and_deterministic_without_jitter():
    policy = RetryPolicy(max_attempts=4, base_delay=2, max_delay=5, jitter=0)
    assert [policy.delay(i) for i in range(1, 5)] == [2, 4, 5, 5]


def test_retry_classification_is_conservative():
    assert classify_transfer_error("UNAUTHORIZED") is RetryClass.UNSAFE
    assert classify_transfer_error("PROTECTED_PRODUCTION") is RetryClass.UNSAFE
    assert classify_transfer_error("TRANSFER_INPUT") is RetryClass.PERMANENT
    assert classify_transfer_error("HTTP_429") is RetryClass.RATE_LIMITED
    assert classify_transfer_error("VERIFY_MISMATCH") is RetryClass.INTEGRITY
    assert classify_transfer_error("NETWORK_RESET") is RetryClass.TRANSIENT


def test_rclone_adapter_builds_non_shell_command():
    commands = []

    def runner(command):
        commands.append(list(command))
        return subprocess.CompletedProcess(command, 0, "ok", "")

    adapter = RcloneAdapter(runner=runner)
    result = adapter.copy("local.bin", "teldrive:path/file.bin", authorization=None, dry_run=True)

    assert result.success is True
    assert commands == [[
        "rclone", "copyto", "local.bin", "teldrive:path/file.bin",
        "--retries", "1", "--low-level-retries", "1", "--dry-run",
    ]]


def test_rclone_mutation_requires_scoped_authorization():
    adapter = RcloneAdapter(runner=lambda command: subprocess.CompletedProcess(command, 0, "", ""))
    result = adapter.copy("local.bin", "otherremote:path/file.bin")
    assert result.success is False
    assert "authorization" in (result.error or "")


def test_rclone_mutation_to_protected_remote_is_blocked_before_authorization():
    adapter = RcloneAdapter(runner=lambda command: subprocess.CompletedProcess(command, 0, "", ""))
    result = adapter.copy("local.bin", "teldrive:path/file.bin")
    assert result.success is False
    assert result.error == "protected production rclone remote"
