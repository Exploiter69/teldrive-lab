"""Controlled Phase 7 host gate; no production mutation is permitted."""

from __future__ import annotations

import tempfile
from pathlib import Path

from teldrive_lab.integrity import IntegrityState, IntegrityStore, duplicate_groups, verify_records
from teldrive_lab.models import (
    DestinationType,
    EncryptionClass,
    FileRecord,
    HashState,
    SourceType,
    VerificationState,
)
from teldrive_lab.safety import Operation, authorize
from teldrive_lab.transfer import sha256_file


def record(path: Path, digest: str | None = None, verification=VerificationState.UNVERIFIED) -> FileRecord:
    size = path.stat().st_size if path.exists() else 0
    return FileRecord(
        path=str(path), name=path.name, parent_path=str(path.parent), size=size,
        mime_type="application/octet-stream", extension=path.suffix, created_at=None, modified_at=None,
        sha256=digest, hash_state=HashState.COMPUTED if digest else HashState.UNKNOWN,
        source_type=SourceType.LOCAL, source_identifier="phase7-host-gate", destination_type=DestinationType.LOCAL,
        destination_identifier=None, telegram_file_id=None, telegram_message_id=None, telegram_channel_id=None,
        encryption_class=EncryptionClass.UNKNOWN, verification_state=verification, tags=None, job_id=None,
        first_seen_at="2026-01-01T00:00:00+00:00", last_seen_at="2026-01-01T00:00:00+00:00",
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="teldrive-lab-phase7-") as root:
        root_path = Path(root)
        a = root_path / "a.bin"
        b = root_path / "b.bin"
        a.write_bytes(b"phase7-duplicate")
        b.write_bytes(b"phase7-duplicate")
        digest = sha256_file(a)

        report = verify_records([record(a, digest)])
        assert report.verified == 1
        assert report.results[0].state is IntegrityState.VERIFIED
        print("SHA-256 verification: PASS")

        store = IntegrityStore(root_path / "integrity.db")
        verify_records([record(a, digest)], store=store)
        assert store.get(str(a)) is not None
        print("Lab-owned checksum evidence database: PASS")

        groups = duplicate_groups([record(a, digest), record(b, digest)])
        assert len(groups) == 1
        assert groups[0].reclaimable_bytes == a.stat().st_size
        print("duplicate grouping by SHA-256 + size: PASS")

        missing = root_path / "missing.bin"
        missing_record = record(missing, "0" * 64, VerificationState.VERIFIED)
        missing_report = verify_records([missing_record])
        assert missing_report.missing == 1
        print("missing verified-copy detection: PASS")

        production = authorize(Operation.DELETE, "/home/thakuralok/TelegramRaw/phase7-gate.txt",
                               explicit_authorization=True)
        assert not production.allowed
        print("destructive production operation remains blocked: PASS")

        outside = root_path / "safe.txt"
        outside.write_text("safe")
        allowed_read = authorize(Operation.READ, outside)
        assert allowed_read.allowed
        print("isolated read-only boundary: PASS")

    print("PHASE 7 HOST GATE: PASS")
    print("production storage mutation: NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
