from __future__ import annotations

from pathlib import Path

from teldrive_lab.models import (
    DestinationType,
    EncryptionClass,
    FileRecord,
    HashState,
    SourceType,
    VerificationState,
)
from teldrive_lab.organization import (
    FileClass,
    OrganizationAction,
    OrganizationExecutor,
    OrganizationPlanner,
    OrganizationPolicy,
    StorageClass,
)


def record(path: Path, *, extension: str | None = None, mime: str | None = None) -> FileRecord:
    return FileRecord(
        path=str(path),
        name=path.name,
        parent_path=str(path.parent),
        size=3,
        mime_type=mime,
        extension=extension or path.suffix,
        created_at="2026-09-11T00:00:00+00:00",
        modified_at="2026-09-11T00:00:00+00:00",
        sha256=None,
        hash_state=HashState.UNKNOWN,
        source_type=SourceType.LOCAL,
        source_identifier="test-host",
        destination_type=DestinationType.LOCAL,
        destination_identifier=None,
        telegram_file_id=None,
        telegram_message_id=None,
        telegram_channel_id=None,
        encryption_class=EncryptionClass.UNKNOWN,
        verification_state=VerificationState.UNVERIFIED,
        tags=None,
        job_id=None,
        first_seen_at="2026-09-11T00:00:00+00:00",
        last_seen_at="2026-09-11T00:00:00+00:00",
    )


def test_path_policy_precedes_extension_and_is_deterministic(tmp_path: Path) -> None:
    source = tmp_path / "projects" / "demo.pdf"
    source.parent.mkdir()
    source.write_bytes(b"abc")
    planner = OrganizationPlanner()

    first = planner.plan([record(source)], raw_root=str(tmp_path / "raw"), crypt_root=str(tmp_path / "crypt"))
    second = planner.plan([record(source)], raw_root=str(tmp_path / "raw"), crypt_root=str(tmp_path / "crypt"))

    item = first.items[0]
    assert item.file_class is FileClass.PROJECT
    assert item.storage_class is StorageClass.CRYPT
    assert item.rule_id == "projects"
    assert item.action is OrganizationAction.COPY
    assert first.digest == second.digest
    assert item.destination.endswith("/project/demo.pdf")


def test_extension_classification_is_deterministic(tmp_path: Path) -> None:
    source = tmp_path / "photo.jpg"
    source.write_bytes(b"abc")
    plan = OrganizationPlanner().plan([record(source)], raw_root=str(tmp_path / "raw"), crypt_root=str(tmp_path / "crypt"))
    item = plan.items[0]
    assert item.file_class is FileClass.IMAGE
    assert item.storage_class is StorageClass.RAW
    assert item.rule_id == "extension:.jpg"


def test_existing_destination_is_conflict_and_never_overwritten(tmp_path: Path) -> None:
    source = tmp_path / "photo.jpg"
    source.write_bytes(b"source")
    raw_root = tmp_path / "raw"
    destination = raw_root / "image" / source.name
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"existing")

    plan = OrganizationPlanner().plan([record(source)], raw_root=str(raw_root), crypt_root=str(tmp_path / "crypt"))
    assert plan.conflict_count == 1
    assert plan.items[0].action is OrganizationAction.CONFLICT
    assert destination.read_bytes() == b"existing"


def test_protected_production_destination_is_blocked(tmp_path: Path) -> None:
    source = tmp_path / "photo.jpg"
    source.write_bytes(b"abc")
    plan = OrganizationPlanner().plan(
        [record(source)], raw_root="/home/thakuralok/TelegramRaw", crypt_root=str(tmp_path / "crypt")
    )
    item = plan.items[0]
    assert item.action is OrganizationAction.BLOCKED
    assert plan.blocked_count == 1


def test_apply_uses_phase4_transfer_boundary(tmp_path: Path) -> None:
    source = tmp_path / "movie.mp4"
    source.write_bytes(b"video-data")
    raw_root = tmp_path / "raw"
    plan = OrganizationPlanner().plan([record(source)], raw_root=str(raw_root), crypt_root=str(tmp_path / "crypt"))

    result = OrganizationExecutor().apply(plan, authorization_id="phase5-test")
    assert result.success
    destination = raw_root / "video" / "movie.mp4"
    assert destination.read_bytes() == b"video-data"


def test_apply_refuses_conflicts_before_mutation(tmp_path: Path) -> None:
    source = tmp_path / "doc.pdf"
    source.write_bytes(b"source")
    raw_root = tmp_path / "raw"
    destination = raw_root / "document" / "doc.pdf"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"existing")
    plan = OrganizationPlanner().plan([record(source)], raw_root=str(raw_root), crypt_root=str(tmp_path / "crypt"))

    try:
        OrganizationExecutor().apply(plan)
    except ValueError as exc:
        assert "conflicting" in str(exc)
    else:
        raise AssertionError("conflicting plan must not be applied")
    assert destination.read_bytes() == b"existing"
