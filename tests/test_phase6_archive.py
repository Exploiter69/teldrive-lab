from __future__ import annotations

import hashlib
from pathlib import Path

from teldrive_lab.archive import ArchiveAction, ArchiveExecutor, ArchivePlanner
from teldrive_lab.models import (
    DestinationType, EncryptionClass, FileRecord, HashState, SourceType, VerificationState,
)


def record(path: Path, *, source_type: SourceType = SourceType.LOCAL, sha256: str | None = None,
           size: int | None = None) -> FileRecord:
    return FileRecord(
        path=str(path), name=path.name, parent_path=str(path.parent), size=size,
        mime_type="text/plain", extension=".txt", created_at=None, modified_at=None,
        sha256=sha256, hash_state=HashState.COMPUTED if sha256 else HashState.UNKNOWN,
        source_type=source_type, source_identifier="phase6-test", destination_type=DestinationType.LOCAL,
        destination_identifier=None, telegram_file_id=None, telegram_message_id=None,
        telegram_channel_id=None, encryption_class=EncryptionClass.UNKNOWN,
        verification_state=VerificationState.UNVERIFIED, tags=None, job_id=None,
        first_seen_at="2026-01-01T00:00:00Z", last_seen_at="2026-01-01T00:00:00Z",
    )


def test_archive_plan_hashes_and_is_stable(tmp_path: Path) -> None:
    source = tmp_path / "sample.txt"
    source.write_text("phase6")
    expected = hashlib.sha256(b"phase6").hexdigest()

    planner = ArchivePlanner()
    first = planner.plan([record(source)], archive_root=str(tmp_path / "archive-root"))
    second = planner.plan([record(source)], archive_root=str(tmp_path / "archive-root"))

    assert first.digest == second.digest
    assert first.items[0].action is ArchiveAction.COPY
    assert first.items[0].candidate.sha256 == expected
    assert first.items[0].candidate.size == 6


def test_non_local_source_is_blocked(tmp_path: Path) -> None:
    source = tmp_path / "remote.txt"
    source.write_text("remote")
    plan = ArchivePlanner().plan(
        [record(source, source_type=SourceType.TELDRIVE)], archive_root=str(tmp_path / "archive-root")
    )
    assert plan.blocked_count == 1
    assert plan.items[0].action is ArchiveAction.BLOCKED


def test_duplicate_is_informational_and_not_applied(tmp_path: Path) -> None:
    source = tmp_path / "new.txt"
    existing = tmp_path / "existing.txt"
    source.write_text("same")
    existing.write_text("same")
    digest = hashlib.sha256(b"same").hexdigest()
    plan = ArchivePlanner().plan(
        [record(source)], archive_root=str(tmp_path / "archive-root"),
        existing_records=[record(existing, sha256=digest, size=4)],
    )
    assert plan.duplicate_count == 1
    assert plan.items[0].action is ArchiveAction.DUPLICATE
    assert existing.exists() and source.exists()


def test_existing_destination_is_conflict(tmp_path: Path) -> None:
    source = tmp_path / "sample.txt"
    source.write_text("content")
    destination = tmp_path / "archive-root" / "archive" / source.name
    destination.parent.mkdir(parents=True)
    destination.write_text("different")

    plan = ArchivePlanner().plan([record(source)], archive_root=str(tmp_path / "archive-root"))
    assert plan.conflict_count == 1
    assert plan.items[0].action is ArchiveAction.CONFLICT
    assert destination.read_text() == "different"


def test_apply_copies_and_verifies_without_deleting_source(tmp_path: Path) -> None:
    source = tmp_path / "sample.txt"
    source.write_text("archive me")
    archive_root = tmp_path / "archive-root"
    plan = ArchivePlanner().plan([record(source)], archive_root=str(archive_root))

    result = ArchiveExecutor().apply(plan)
    destination = archive_root / "archive" / source.name

    assert result.success
    assert len(result.results) == 1
    assert result.results[0].verified
    assert source.exists()
    assert destination.read_text() == "archive me"


def test_protected_production_destination_is_blocked_before_apply(tmp_path: Path) -> None:
    source = tmp_path / "sample.txt"
    source.write_text("protected")
    plan = ArchivePlanner().plan([record(source)], archive_root="/home/thakuralok/TelegramRaw")
    assert plan.blocked_count == 1
    assert plan.items[0].action is ArchiveAction.BLOCKED
    assert source.exists()


def test_apply_rejects_duplicate_plan(tmp_path: Path) -> None:
    source = tmp_path / "new.txt"
    existing = tmp_path / "existing.txt"
    source.write_text("same")
    existing.write_text("same")
    digest = hashlib.sha256(b"same").hexdigest()
    plan = ArchivePlanner().plan(
        [record(source)], archive_root=str(tmp_path / "archive-root"),
        existing_records=[record(existing, sha256=digest, size=4)],
    )

    try:
        ArchiveExecutor().apply(plan)
    except ValueError as exc:
        assert "duplicate" in str(exc)
    else:
        raise AssertionError("duplicate archive plan must require review")
