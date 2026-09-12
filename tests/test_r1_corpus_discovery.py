from __future__ import annotations

from pathlib import Path

import pytest

from teldrive_lab.catalog import Catalog
from teldrive_lab.corpus import CorpusLimits, RcloneTelDriveSource, discover_teldrive
from teldrive_lab.models import SourceType


def _fake_rclone(path: Path, rows: list[str], *, exit_code: int = 0) -> None:
    path.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        f"rows = {rows!r}\n"
        "sys.stdout.write(''.join(rows))\n"
        f"sys.exit({exit_code})\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def test_discovery_ingests_telldrive_metadata_without_content_reads(tmp_path: Path) -> None:
    catalog = Catalog(tmp_path / "catalog.db")
    fake = tmp_path / "rclone"
    _fake_rclone(
        fake,
        [
            '"Movies/one.mkv",1024,"2026-09-12T01:02:03Z"\n',
            '"Docs/report.pdf",2048,"2026-09-11T01:02:03Z"\n',
        ],
    )

    result = discover_teldrive(
        catalog,
        remote="teldrive:",
        executable=str(fake),
        limits=CorpusLimits(max_entries=10, timeout_seconds=5),
    )

    assert result.discovered == 2
    assert result.bounded is False
    assert result.stale_paths == ()
    records = catalog.list_source(SourceType.TELDRIVE, "rclone:teldrive:teldrive")
    assert [record.path for record in records] == ["Docs/report.pdf", "Movies/one.mkv"]
    assert all(record.sha256 is None for record in records)
    assert all(record.source_type == SourceType.TELDRIVE for record in records)


def test_discovery_is_bounded_and_reports_stale_without_deleting(tmp_path: Path) -> None:
    catalog = Catalog(tmp_path / "catalog.db")
    fake = tmp_path / "rclone"
    _fake_rclone(fake, ['"new.bin",12,"2026-09-12T01:02:03Z"\n'])

    first = discover_teldrive(catalog, remote="teldrive:", executable=str(fake))
    assert first.discovered == 1

    _fake_rclone(fake, [])
    second = discover_teldrive(catalog, remote="teldrive:", executable=str(fake))
    assert second.discovered == 0
    assert second.stale_paths == ("new.bin",)
    assert catalog.count() == 1

    _fake_rclone(
        fake,
        [
            '"a.bin",1,"2026-09-12T01:02:03Z"\n',
            '"b.bin",2,"2026-09-12T01:02:03Z"\n',
            '"c.bin",3,"2026-09-12T01:02:03Z"\n',
        ],
    )
    bounded = discover_teldrive(
        catalog,
        remote="other:",
        executable=str(fake),
        limits=CorpusLimits(max_entries=2, timeout_seconds=5),
    )
    assert bounded.discovered == 2
    assert bounded.bounded is True


def test_remote_validation_and_failure_boundary(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        RcloneTelDriveSource("not-a-remote")

    fake = tmp_path / "rclone"
    _fake_rclone(fake, [], exit_code=7)
    catalog = Catalog(tmp_path / "catalog.db")
    with pytest.raises(Exception, match="rclone exited with status 7"):
        discover_teldrive(catalog, remote="teldrive:", executable=str(fake))
