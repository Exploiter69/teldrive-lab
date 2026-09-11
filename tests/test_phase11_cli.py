from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from teldrive_lab.catalog import Catalog
from teldrive_lab.cli import main
from teldrive_lab.jobs import JobState, JobStore, JobType
from teldrive_lab.models import EncryptionClass, FileRecord, HashState, SourceType, VerificationState


def record(path: str, name: str) -> FileRecord:
    return FileRecord(
        path=path, name=name, parent_path=str(Path(path).parent), size=3,
        mime_type="text/plain", extension=".txt", created_at=None, modified_at=None,
        sha256=None, hash_state=HashState.UNKNOWN, source_type=SourceType.LOCAL,
        source_identifier="test", destination_type=None, destination_identifier=None,
        telegram_file_id=None, telegram_message_id=None, telegram_channel_id=None,
        encryption_class=EncryptionClass.UNKNOWN, verification_state=VerificationState.UNVERIFIED,
        tags=None, job_id=None, first_seen_at="now", last_seen_at="now",
    )


def test_catalog_search_is_read_only(tmp_path: Path) -> None:
    catalog = Catalog(tmp_path / "catalog.db")
    catalog.upsert(record(str(tmp_path / "alpha.txt"), "alpha.txt"))
    catalog.upsert(record(str(tmp_path / "beta.bin"), "beta.bin"))
    before = catalog.count()
    results = catalog.search("alpha")
    assert [item.name for item in results] == ["alpha.txt"]
    assert catalog.count() == before


def test_job_listing_is_deterministic(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.db")
    first = store.enqueue(JobType.INDEX, job_id="b")
    second = store.enqueue(JobType.VERIFY, job_id="a")
    assert {j.job_id for j in store.list_jobs(limit=10)} == {first.job_id, second.job_id}
    assert [j.job_id for j in store.list_jobs(state=JobState.QUEUED, limit=10)] == ["a", "b"]


def test_cli_job_controls_are_audited(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("TELDRIVE_LAB_STATE", str(tmp_path / "runtime"))
    store = JobStore(tmp_path / "runtime" / "state" / "jobs.db")
    job = store.enqueue(JobType.INDEX, job_id="job-cli")
    claimed = store.claim("worker-1")
    assert claimed is not None
    import sys
    monkeypatch.setattr(sys, "argv", ["td", "pause", job.job_id])
    assert main() == 0
    output = json.loads(capsys.readouterr().out)
    assert output["job"]["state"] == "PAUSED"
    with sqlite3.connect(tmp_path / "runtime" / "state" / "audit.db") as conn:
        row = conn.execute("SELECT operation,decision,result FROM events ORDER BY id DESC LIMIT 1").fetchone()
    assert row == ("JOB_CONTROL", "EXPLICIT_OPERATOR_ACTION", "PAUSED")


def test_cli_search_and_health_are_read_only(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("TELDRIVE_LAB_STATE", str(tmp_path / "runtime"))
    import sys
    monkeypatch.setattr(sys, "argv", ["td", "health"])
    assert main() == 0
    health = json.loads(capsys.readouterr().out)
    assert isinstance(health, list)
    assert all({"name", "ok", "detail"} <= set(item) for item in health)
    monkeypatch.setattr(sys, "argv", ["td", "init"])
    assert main() == 0
    init = json.loads(capsys.readouterr().out)
    assert str(tmp_path / "runtime") in init["runtime"]
