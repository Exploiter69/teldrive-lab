#!/usr/bin/env python3
"""Controlled Phase 6 host gate using only temporary Lab-owned data."""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from teldrive_lab.archive import ArchiveAction, ArchiveExecutor, ArchivePlanner
from teldrive_lab.models import DestinationType, EncryptionClass, FileRecord, HashState, SourceType, VerificationState


def make_record(path: Path) -> FileRecord:
    return FileRecord(
        path=str(path), name=path.name, parent_path=str(path.parent), size=path.stat().st_size,
        mime_type="text/plain", extension=path.suffix, created_at=None, modified_at=None,
        sha256=None, hash_state=HashState.UNKNOWN, source_type=SourceType.LOCAL,
        source_identifier="phase6-host-gate", destination_type=DestinationType.LOCAL,
        destination_identifier=None, telegram_file_id=None, telegram_message_id=None,
        telegram_channel_id=None, encryption_class=EncryptionClass.UNKNOWN,
        verification_state=VerificationState.UNVERIFIED, tags=None, job_id=None,
        first_seen_at="2026-01-01T00:00:00Z", last_seen_at="2026-01-01T00:00:00Z",
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="teldrive-lab-phase6-") as root:
        root_path = Path(root)
        source = root_path / "archive-me.txt"
        source.write_text("phase6 archive gate\n")
        archive_root = root_path / "archive-root"

        plan = ArchivePlanner().plan([make_record(source)], archive_root=str(archive_root))
        assert plan.copy_count == 1
        assert plan.digest == ArchivePlanner().plan([make_record(source)], archive_root=str(archive_root)).digest
        print("- deterministic archive plan and SHA-256: PASS")

        result = ArchiveExecutor().apply(plan, authorization_id="phase6-host-gate")
        destination = archive_root / "archive" / source.name
        assert result.success and result.results[0].verified
        assert source.exists() and destination.read_text() == source.read_text()
        assert hashlib.sha256(source.read_bytes()).hexdigest() == hashlib.sha256(destination.read_bytes()).hexdigest()
        print("- isolated archive transfer + verification: PASS")

        protected = ArchivePlanner().plan([make_record(source)], archive_root="/home/thakuralok/TelegramRaw")
        assert protected.items[0].action is ArchiveAction.BLOCKED
        assert source.exists()
        print("- protected production destination blocked before mutation: PASS")

        duplicate = root_path / "duplicate.txt"
        duplicate.write_text(source.read_text())
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        existing = make_record(duplicate)
        existing = FileRecord(**{**existing.__dict__, "sha256": digest, "hash_state": HashState.COMPUTED}) if hasattr(existing, "__dict__") else existing
        # Build the duplicate record without relying on dataclass __dict__ for slots.
        existing = FileRecord(
            path=existing.path, name=existing.name, parent_path=existing.parent_path, size=existing.size,
            mime_type=existing.mime_type, extension=existing.extension, created_at=existing.created_at,
            modified_at=existing.modified_at, sha256=digest, hash_state=HashState.COMPUTED,
            source_type=existing.source_type, source_identifier=existing.source_identifier,
            destination_type=existing.destination_type, destination_identifier=existing.destination_identifier,
            telegram_file_id=existing.telegram_file_id, telegram_message_id=existing.telegram_message_id,
            telegram_channel_id=existing.telegram_channel_id, encryption_class=existing.encryption_class,
            verification_state=existing.verification_state, tags=existing.tags, job_id=existing.job_id,
            first_seen_at=existing.first_seen_at, last_seen_at=existing.last_seen_at, id=existing.id,
        )
        dup_plan = ArchivePlanner().plan([make_record(source)], archive_root=str(root_path / "dup-root"), existing_records=[existing])
        assert dup_plan.items[0].action is ArchiveAction.DUPLICATE
        print("- informational duplicate detection: PASS")

    print("PHASE 6 HOST GATE: PASS")
    print("- production storage mutation: NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
