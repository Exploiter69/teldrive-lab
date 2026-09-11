from pathlib import Path

from teldrive_lab.safety import AuthorizationReceipt, Operation
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


def test_lab_transfer_requires_and_accepts_scoped_authorization(tmp_path: Path):
    source = tmp_path / "source.txt"
    destination = tmp_path / "out" / "copy.txt"
    source.write_text("phase4")
    spec = TransferSpec(str(source), str(destination))

    denied = TransferManager().transfer(spec)
    assert not denied.success
    assert "authorization" in (denied.error or "")

    receipt = AuthorizationReceipt.for_paths(Operation.TRANSFER, str(source), str(destination))
    result = TransferManager().transfer(spec, authorization=receipt)

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
    spec = TransferSpec(str(source), str(destination))
    receipt = AuthorizationReceipt.for_paths(Operation.TRANSFER, str(source), str(destination))

    result = TransferManager().transfer(spec, authorization=receipt)

    assert not result.success
    assert "exists" in (result.error or "")
    assert destination.read_text() == "old"


def test_protected_production_destination_is_blocked_even_with_authorization(tmp_path: Path):
    source = tmp_path / "source.txt"
    source.write_text("must not reach production")
    destination = "/home/thakuralok/TelegramRaw/phase4-test.txt"
    receipt = AuthorizationReceipt.for_paths(Operation.TRANSFER, str(source), destination)

    result = TransferManager().transfer(
        TransferSpec(str(source), destination),
        authorization=receipt,
    )

    assert not result.success
    assert result.bytes_transferred == 0
    assert "protected" in (result.error or "").lower()


def test_denied_production_transfer_performs_no_filesystem_side_effects(tmp_path: Path, monkeypatch):
    source = tmp_path / "source.txt"
    source.write_text("must not reach production")
    destination = "/home/thakuralok/TelegramRaw/phase4-test.txt"
    receipt = AuthorizationReceipt.for_paths(Operation.TRANSFER, str(source), destination)
    mkdir_calls: list[object] = []

    original_mkdir = Path.mkdir

    def fail_if_mkdir_called(self, *args, **kwargs):
        mkdir_calls.append(self)
        return original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fail_if_mkdir_called)

    result = TransferManager().transfer(
        TransferSpec(str(source), destination),
        authorization=receipt,
    )

    assert not result.success
    assert "protected" in (result.error or "").lower()
    assert mkdir_calls == []


def test_checksum_helper_is_deterministic(tmp_path: Path):
    source = tmp_path / "source.bin"
    source.write_bytes(b"checksum")
    destination = tmp_path / "copy.bin"
    receipt = AuthorizationReceipt.for_paths(Operation.TRANSFER, str(source), str(destination))
    manager = TransferManager()
    result = manager.transfer(
        TransferSpec(str(source), str(destination)),
        authorization=receipt,
    )
    assert result.verified
    assert result.source_sha256 == result.destination_sha256
