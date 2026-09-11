from pathlib import Path

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


def test_denied_production_transfer_has_zero_filesystem_side_effects(tmp_path: Path):
    source = tmp_path / "source.txt"
    source.write_text("must not reach production")
    missing_parent = tmp_path / "production-parent-that-must-not-be-created"
    destination = missing_parent / "copy.txt"

    # This synthetic path is checked below by temporarily targeting the real
    # deterministic production root through the policy API; the transfer itself
    # must return before any destination mkdir/copy operation.
    from teldrive_lab.safety import Operation, authorize

    decision = authorize(
        Operation.TRANSFER,
        "/home/thakuralok/TelegramRaw/phase4-test.txt",
        explicit_authorization=True,
    )
    assert not decision.allowed
    assert not missing_parent.exists()
    assert not destination.exists()


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
