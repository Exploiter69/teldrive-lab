from __future__ import annotations

from teldrive_lab.catalog import Catalog
from teldrive_lab.models import DestinationType, EncryptionClass, FileRecord, HashState, SourceType, VerificationState
from teldrive_lab.search import SearchError, UnifiedSearch, parse_query, parse_size


def record(path: str, *, source=SourceType.TELDRIVE, size=100, mime="video/mp4", tags=("r1-discovered",)) -> FileRecord:
    return FileRecord(
        path=path, name=path.rsplit("/", 1)[-1], parent_path=path.rsplit("/", 1)[0] if "/" in path else None,
        size=size, mime_type=mime, extension="." + path.rsplit(".", 1)[-1].lower() if "." in path else None,
        created_at="2026-01-01T00:00:00+00:00", modified_at="2026-09-01T00:00:00+00:00",
        sha256=None, hash_state=HashState.UNKNOWN, source_type=source, source_identifier="rclone:teldrive:teldrive",
        destination_type=DestinationType.TELDRIVE, destination_identifier="teldrive", telegram_file_id=None,
        telegram_message_id=None, telegram_channel_id=None, encryption_class=EncryptionClass.UNKNOWN,
        verification_state=VerificationState.UNVERIFIED, tags=tags, job_id=None,
        first_seen_at="2026-09-01T00:00:00+00:00", last_seen_at="2026-09-01T00:00:00+00:00",
    )


def test_fts_search_is_unified_and_auto_rebuilds(tmp_path):
    catalog = Catalog(tmp_path / "catalog.db")
    catalog.upsert(record("Movies/Dune Part Two.mkv", size=2_000_000))
    catalog.upsert(record("Music/Dune soundtrack.flac", size=5_000_000, mime="audio/flac"))
    search = UnifiedSearch(catalog)
    page = search.search("dune")
    assert page.total == 2
    assert page.index_rebuilt is True
    assert [hit.record.name for hit in page.hits] == ["Dune Part Two.mkv", "Dune soundtrack.flac"]
    catalog.upsert(record("Books/Dune.epub", size=10_000, mime="application/epub+zip"))
    page = search.search("dune")
    assert page.total == 3
    assert page.index_rebuilt is True


def test_structured_filters_sort_and_pagination(tmp_path):
    catalog = Catalog(tmp_path / "catalog.db")
    catalog.upsert(record("A/big.mp4", size=5_000_000))
    catalog.upsert(record("B/small.mp4", size=2_000))
    catalog.upsert(record("C/other.txt", size=9_000, mime="text/plain"))
    page = UnifiedSearch(catalog).search(parse_query("source:TELDRIVE ext:mp4 min_size:1mb sort:size order:desc limit:1"))
    assert page.total == 1
    assert page.hits[0].record.name == "big.mp4"
    assert parse_size("1.5gb") == int(1.5 * 1024**3)


def test_path_tag_and_empty_text_filters(tmp_path):
    catalog = Catalog(tmp_path / "catalog.db")
    catalog.upsert(record("Movies/a.mp4", tags=("r1-discovered", "favorite")))
    catalog.upsert(record("Music/b.mp3", mime="audio/mpeg", tags=("r1-discovered",)))
    search = UnifiedSearch(catalog)
    page = search.search("path:Movies tag:favorite")
    assert page.total == 1
    assert page.hits[0].record.path == "Movies/a.mp4"
    assert search.search(parse_query("ext:mp3")).total == 1


def test_search_is_read_only_and_rejects_bad_queries(tmp_path):
    catalog = Catalog(tmp_path / "catalog.db")
    catalog.upsert(record("a.txt", mime="text/plain"))
    search = UnifiedSearch(catalog)
    before = catalog.count()
    page = search.search("a")
    assert page.hits[0].record.path == "a.txt"
    assert catalog.count() == before
    assert search.search("").total == 1
    for query in ("limit:0", "limit:501", "min_size:2gb max_size:1gb", "source:NOPE", "sort:bad"):
        try:
            search.search(query)
        except (SearchError, ValueError):
            pass
        else:
            raise AssertionError(f"query should fail: {query}")
