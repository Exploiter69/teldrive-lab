from __future__ import annotations

import sqlite3

from teldrive_lab.catalog import Catalog
from teldrive_lab.indexer import IndexLimits, Indexer
from teldrive_lab.models import (
    DestinationType,
    EncryptionClass,
    FileRecord,
    HashState,
    SourceType,
    VerificationState,
)


def make_record(path: str = "/tmp/example.txt", seen: str = "2026-09-11T00:00:00+00:00") -> FileRecord:
    return FileRecord(
        path=path,
        name="example.txt",
        parent_path="/tmp",
        size=12,
        mime_type=None,
        extension=".txt",
        created_at=None,
        modified_at="2026-09-10T00:00:00+00:00",
        sha256=None,
        hash_state=HashState.UNKNOWN,
        source_type=SourceType.LOCAL,
        source_identifier="test-root",
        destination_type=DestinationType.LOCAL,
        destination_identifier="test-destination",
        telegram_file_id=None,
        telegram_message_id=None,
        telegram_channel_id=None,
        encryption_class=EncryptionClass.UNKNOWN,
        verification_state=VerificationState.UNVERIFIED,
        tags=None,
        job_id=None,
        first_seen_at=seen,
        last_seen_at=seen,
    )


def test_catalog_creates_schema_and_indexes(tmp_path):
    catalog = Catalog(tmp_path / "catalog.db")

    assert catalog.schema_version() == 1
    assert catalog.count() == 0

    with sqlite3.connect(tmp_path / "catalog.db") as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        indexes = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            )
        }

    assert {"schema_version", "files"} <= tables
    assert "idx_files_path" in indexes
    assert "idx_files_source" in indexes


def test_upsert_is_deterministic_and_preserves_first_seen(tmp_path):
    catalog = Catalog(tmp_path / "catalog.db")
    first = make_record(seen="2026-09-01T00:00:00+00:00")
    second = make_record(seen="2026-09-11T00:00:00+00:00")
    second = FileRecord(**{**second.__dict__, "size": 99}) if hasattr(second, "__dict__") else FileRecord(
        **{field: getattr(second, field) for field in second.__dataclass_fields__},
        size=99,
    )

    stored_first = catalog.upsert(first)
    stored_second = catalog.upsert(second)

    assert stored_first.id == stored_second.id
    assert stored_second.size == 99
    assert stored_second.first_seen_at == "2026-09-01T00:00:00+00:00"
    assert stored_second.last_seen_at == "2026-09-11T00:00:00+00:00"
    assert catalog.count() == 1


def test_reconcile_reports_missing_without_deleting(tmp_path):
    catalog = Catalog(tmp_path / "catalog.db")
    catalog.upsert(make_record("/tmp/a.txt"))
    catalog.upsert(make_record("/tmp/b.txt"))

    missing = catalog.reconcile_source(SourceType.LOCAL, "test-root", ["/tmp/a.txt"])

    assert [record.path for record in missing] == ["/tmp/b.txt"]
    assert catalog.count() == 2


def test_rebuild_resets_only_lab_catalog(tmp_path):
    catalog = Catalog(tmp_path / "catalog.db")
    catalog.upsert(make_record())
    catalog.rebuild()

    assert catalog.schema_version() == 1
    assert catalog.count() == 0


def test_indexer_is_metadata_only_and_bounded(tmp_path):
    root = tmp_path / "source"
    nested = root / "nested"
    nested.mkdir(parents=True)
    (root / "a.txt").write_text("hello", encoding="utf-8")
    (nested / "b.bin").write_bytes(b"1234")
    (root / "link.txt").symlink_to(root / "a.txt")

    catalog = Catalog(tmp_path / "catalog.db")
    result = Indexer(catalog, IndexLimits(max_entries=10, max_depth=8)).scan(root)

    assert result.indexed == 3
    assert result.skipped == 1
    assert not result.bounded
    assert catalog.count() == 3
    assert catalog.get(SourceType.LOCAL, str(root), str(root / "a.txt")).size == 5
    assert catalog.get(SourceType.LOCAL, str(root), str(nested)).size is None
    assert catalog.get(SourceType.LOCAL, str(root), str(root / "link.txt")) is None


def test_indexer_stops_at_entry_bound(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    for name in ("a", "b", "c"):
        (root / name).write_text(name, encoding="utf-8")

    catalog = Catalog(tmp_path / "catalog.db")
    result = Indexer(catalog, IndexLimits(max_entries=2, max_depth=8)).scan(root)

    assert result.indexed == 2
    assert result.bounded
    assert catalog.count() == 2
