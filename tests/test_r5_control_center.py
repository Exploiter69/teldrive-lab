from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

from teldrive_lab.catalog import Catalog
from teldrive_lab.control_center import ControlCenter, control_center_server
from teldrive_lab.jobs import JobType
from teldrive_lab.models import (
    EncryptionClass, FileRecord, HashState, SourceType, VerificationState,
)


def _record(path: str) -> FileRecord:
    return FileRecord(
        path=path, name=path.rsplit("/", 1)[-1], parent_path="/media", size=123,
        mime_type="video/mp4", extension=".mp4", created_at=None, modified_at=None,
        sha256=None, hash_state=HashState.UNKNOWN, source_type=SourceType.TELDRIVE,
        source_identifier="teldrive", destination_type=None, destination_identifier=None,
        telegram_file_id=None, telegram_message_id=None, telegram_channel_id=None,
        encryption_class=EncryptionClass.RAW, verification_state=VerificationState.UNVERIFIED,
        tags=None, job_id=None, first_seen_at="2026-01-01T00:00:00+00:00", last_seen_at="2026-01-01T00:00:00+00:00",
    )


def test_r5_live_payload_reads_catalog_jobs_and_audit(tmp_path):
    catalog = Catalog(tmp_path / "catalog.db")
    catalog.upsert(_record("/media/movie.mp4"))
    center = ControlCenter(tmp_path)
    job = center.jobs.enqueue(JobType.BACKUP, path="/media/movie.mp4")
    payload = center.dashboard()
    assert payload["schema"] == "teldrive-lab.control-center.v1"
    assert payload["authority"] == "teldrive"
    assert payload["ui_mutation_policy"] == "none"
    assert payload["catalog"]["total"] == 1
    assert payload["jobs"]["total_known"] == 1
    assert payload["jobs"]["items"][0]["job_id"] == job.job_id
    assert payload["media"]["total"] == 1
    assert "/api/audit" in payload["routes"]


def test_r5_search_is_live(tmp_path):
    catalog = Catalog(tmp_path / "catalog.db")
    catalog.upsert(_record("/media/movie.mp4"))
    result = ControlCenter(tmp_path).search_state("movie")
    assert result["count"] == 1
    assert result["items"][0]["name"] == "movie.mp4"


def test_r5_http_is_read_only_and_loopback(tmp_path):
    server = control_center_server(tmp_path, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/api/dashboard"
        with urllib.request.urlopen(url, timeout=3) as response:
            payload = json.loads(response.read())
        assert payload["authority"] == "teldrive"
        request = urllib.request.Request(url, method="POST")
        try:
            urllib.request.urlopen(request, timeout=3)
            raise AssertionError("POST unexpectedly succeeded")
        except urllib.error.HTTPError as exc:
            assert exc.code == 405
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)
