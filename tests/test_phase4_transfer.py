from pathlib import Path

import teldrive_lab.transfer as transfer_module
from teldrive_lab.transfer import TransferManager, TransferSpec


def test_plan_is_read_only_and_reports_source(tmp_path: Path):
    source = tmp_path / "source.txt"
    destination = tmp_path / "out" / "copy.txt"
    source.write_text("phase4")

    plan = TransferManager().plan(TransferSpec(str(source), str(destination)))

    assert plan.source_exists
    assert plan.source_size == 6
    assert not plan.destination_exists
    assert not plan.allowed
    assert "authorization" in plan.reason
    assert not destination.exists()


def test_lab_transfer_requires_and_accepts_explicit_authorization(tmp_path: Path):
    source = tmp_path / "source.txt"
    destination = tmp_path / "out" / "copy.txt"
    source.write_text("phase4")

    denied = TransferManager().transfer(TransferSpec(str(source), str(destination)))
    assert not denied.success
    assert "authorization" in (denied.error or "")

    result = TransferManager().transfer(
        TransferSpec(str(source), str(destination)), explicit_authorization=True
    )

    assert result.success
    assert result.verified
    assert result.source_sha256 == result.destination_sha256
    assert result.bytes_transferred == 6
    assert destination.read_text() == "phase4"


def test_existing_destination_is_not_overwritten(tmp_path: Path):
    source = tmp_path / "source.txt"
    destination = tmp_path / "copy.txt"
    source.write_text("new")
    destination.write_text("old")

    result = TransferManager().transfer(
        TransferSpec(str(source), str(destination)), explicit_authorization=True
    )

    assert not result.success
    assert "exists" in (result.error or "")
    assert destination.read_text() == "old"


def test_protected_production_destination_is_blocked_even_with_authorization(tmp_path: Path):
    source = tmp_path / "source.txt"
    source.write_text("must not reach production")

    result = TransferManager().transfer(
        TransferSpec(str(source), "/home/thakuralok/TelegramRaw/phase4-test.txt"),
        explicit_authorization=True,
    )

    assert not result.success
    assert result.bytes_transferred == 0
    assert "protected" in (result.error or "").lower()


def test_denied_production_transfer_performs_no_filesystem_side_effects(tmp_path: Path, monkeypatch):
    source = tmp_path / "source.txt"
    source.write_text("must not reach production")
    destination = "/home/thakuralok/TelegramRaw/phase4-test.txt"
    mkdir_calls: list[object] = []
    copy_calls: list[object] = []

    original_mkdir = Path.mkdir

    def fail_if_mkdir_called(self, *args, **kwargs):
        mkdir_calls.append(self)
        return original_mkdir(self, *args, **kwargs)

    def fail_if_copy_called(*args, **kwargs):
        copy_calls.append(args[1] if len(args) > 1 else None)
        raise AssertionError("copy2 must not run after a production safety denial")

    monkeypatch.setattr(Path, "mkdir", fail_if_mkdir_called)
    monkeypatch.setattr(transfer_module, "copy2", fail_if_copy_called)

    result = TransferManager().transfer(
        TransferSpec(str(source), destination), explicit_authorization=True
    )

    assert not result.success
    assert "protected" in (result.error or "").lower()
    assert mkdir_calls == []
    assert copy_calls == []


def test_checksum_helper_is_deterministic(tmp_path: Path):
    source = tmp_path / "source.bin"
    source.write_bytes(b"checksum")
    manager = TransferManager()
    result = manager.transfer(
        TransferSpec(str(source), str(tmp_path / "copy.bin")),
        explicit_authorization=True,
    )
    assert result.verified
    assert result.source_sha256 == result.destination_sha256
