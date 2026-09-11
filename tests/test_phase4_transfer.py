from pathlib import Path

from teldrive_lab.transfer import TransferManager, TransferSpec


def test_lab_transfer_copies_without_overwrite(tmp_path: Path):
    source = tmp_path / "source.txt"
    destination = tmp_path / "out" / "copy.txt"
    source.write_text("phase4")

    result = TransferManager().transfer(TransferSpec(str(source), str(destination)))

    assert result.success
    assert result.bytes_transferred == 6
    assert destination.read_text() == "phase4"


def test_existing_destination_is_not_overwritten(tmp_path: Path):
    source = tmp_path / "source.txt"
    destination = tmp_path / "copy.txt"
    source.write_text("new")
    destination.write_text("old")

    result = TransferManager().transfer(TransferSpec(str(source), str(destination)))

    assert not result.success
    assert "exists" in (result.error or "")
    assert destination.read_text() == "old"


def test_protected_production_destination_is_blocked(tmp_path: Path):
    source = tmp_path / "source.txt"
    source.write_text("must not reach production")

    result = TransferManager().transfer(
        TransferSpec(str(source), "/home/thakuralok/TelegramRaw/phase4-test.txt")
    )

    assert not result.success
    assert result.bytes_transferred == 0
    assert "protected" in (result.error or "").lower() or "authorization" in (result.error or "").lower()
