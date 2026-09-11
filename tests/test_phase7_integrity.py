from pathlib import Path

from teldrive_lab.integrity import (
    IntegrityState,
    IntegrityStore,
    benchmark_hash_algorithms,
    duplicate_groups,
    missing_verified_copies,
    stale_checksum_paths,
    verify_path,
    verify_records,
)
from teldrive_lab.models import (
    DestinationType,
    EncryptionClass,
    FileRecord,
    HashState,
    SourceType,
    VerificationState,
)
from teldrive_lab.transfer import sha256_file


def make_record(path: Path, *, digest: str | None = None,
                verification: VerificationState = VerificationState.UNVERIFIED) -> FileRecord:
    return FileRecord(
        path=str(path), name=path.name, parent_path=str(path.parent), size=path.stat().st_size if path.exists() else 0,
        mime_type="application/octet-stream", extension=path.suffix, created_at=None, modified_at=None,
        sha256=digest, hash_state=HashState.COMPUTED if digest else HashState.UNKNOWN,
        source_type=SourceType.LOCAL, source_identifier="phase7-test", destination_type=DestinationType.LOCAL,
        destination_identifier=None, telegram_file_id=None, telegram_message_id=None, telegram_channel_id=None,
        encryption_class=EncryptionClass.UNKNOWN, verification_state=verification, tags=None, job_id=None,
        first_seen_at="2026-01-01T00:00:00+00:00", last_seen_at="2026-01-01T00:00:00+00:00",
    )


def test_verify_path_passes_sha256_and_size(tmp_path: Path):
    path = tmp_path / "file.bin"
    path.write_bytes(b"phase7-integrity")
    digest = sha256_file(path)
    result = verify_path(path, expected_sha256=digest, expected_size=path.stat().st_size)
    assert result.state is IntegrityState.VERIFIED
    assert result.verified


def test_verify_path_detects_missing_changed_and_mismatch(tmp_path: Path):
    missing = verify_path(tmp_path / "missing.bin", expected_sha256="abc", expected_size=3)
    assert missing.state is IntegrityState.MISSING

    path = tmp_path / "changed.bin"
    path.write_bytes(b"12345")
    changed = verify_path(path, expected_sha256="0" * 64, expected_size=3)
    assert changed.state is IntegrityState.CHANGED

    digest = sha256_file(path)
    path.write_bytes(b"54321")
    mismatch = verify_path(path, expected_sha256=digest, expected_size=5)
    assert mismatch.state is IntegrityState.MISMATCH


def test_verify_records_writes_lab_owned_checksum_evidence(tmp_path: Path):
    path = tmp_path / "evidence.txt"
    path.write_text("evidence")
    record = make_record(path, digest=sha256_file(path))
    store = IntegrityStore(tmp_path / "integrity.db")
    report = verify_records([record], store=store)
    assert report.verified == 1
    evidence = store.get(str(path))
    assert evidence is not None
    assert evidence.sha256 == record.sha256


def test_duplicate_groups_are_informational_and_deterministic(tmp_path: Path):
    a = tmp_path / "a.bin"
    b = tmp_path / "b.bin"
    c = tmp_path / "c.bin"
    a.write_bytes(b"duplicate")
    b.write_bytes(b"duplicate")
    c.write_bytes(b"different")
    da = sha256_file(a)
    dc = sha256_file(c)
    groups = duplicate_groups([
        make_record(b, digest=da), make_record(a, digest=da), make_record(c, digest=dc)
    ])
    assert len(groups) == 1
    assert groups[0].paths == tuple(sorted((str(a), str(b))))
    assert groups[0].reclaimable_bytes == a.stat().st_size


def test_missing_verified_copies_report_only(tmp_path: Path):
    present = tmp_path / "present"
    missing = tmp_path / "missing"
    present.write_text("present")
    records = [
        make_record(present, verification=VerificationState.VERIFIED),
        make_record(missing, verification=VerificationState.VERIFIED),
    ]
    assert missing_verified_copies(records) == (str(missing),)


def test_stale_checksum_evidence_detects_size_or_mtime_change(tmp_path: Path):
    path = tmp_path / "stale"
    path.write_text("before")
    store = IntegrityStore(tmp_path / "integrity.db")
    verify_records([make_record(path, digest=sha256_file(path))], store=store)
    path.write_text("after-with-different-size")
    assert stale_checksum_paths([make_record(path)], store) == (str(path),)


def test_benchmark_uses_sha256_and_does_not_require_blake3(tmp_path: Path):
    path = tmp_path / "bench"
    path.write_bytes(b"x" * 4096)
    result = benchmark_hash_algorithms(path)
    assert result["bytes"] == 4096
    assert isinstance(result["sha256_seconds"], float)
    assert len(result["sha256"]) == 64
    assert result["blake3"] == "unavailable" or isinstance(result["blake3"], str)
