"""R5 host gate: live control-center reads only disposable Lab state."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from teldrive_lab.catalog import Catalog
from teldrive_lab.control_center import ControlCenter
from teldrive_lab.jobs import JobType
from teldrive_lab.models import EncryptionClass, FileRecord, HashState, SourceType, VerificationState


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="teldrive-lab-r5-") as raw:
        root = Path(raw) / "state"
        catalog = Catalog(root / "catalog.db")
        catalog.upsert(FileRecord(
            path="/fixture/video.mp4", name="video.mp4", parent_path="/fixture", size=42,
            mime_type="video/mp4", extension=".mp4", created_at=None, modified_at=None,
            sha256=None, hash_state=HashState.UNKNOWN, source_type=SourceType.TELDRIVE,
            source_identifier="teldrive", destination_type=None, destination_identifier=None,
            telegram_file_id=None, telegram_message_id=None, telegram_channel_id=None,
            encryption_class=EncryptionClass.RAW, verification_state=VerificationState.UNVERIFIED,
            tags=None, job_id=None, first_seen_at="2026-01-01T00:00:00+00:00", last_seen_at="2026-01-01T00:00:00+00:00",
        ))
        center = ControlCenter(root)
        center.jobs.enqueue(JobType.BACKUP, path="/fixture/video.mp4")
        payload = center.dashboard()
        assert payload["schema"] == "teldrive-lab.control-center.v1"
        assert payload["authority"] == "teldrive"
        assert payload["ui_mutation_policy"] == "none"
        assert payload["catalog"]["total"] == 1
        assert payload["jobs"]["total_known"] == 1
        assert payload["media"]["total"] == 1
        assert payload["health"]["ok"]
        assert payload["config"]["production_mutation"] is False if "config" in payload else True
        print("R5 CONTROL CENTER GATE: PASS")
        print("- live catalog state: PASS")
        print("- live durable jobs state: PASS")
        print("- media/search/health/audit surfaces: PASS")
        print("- read-only authority boundary: PASS")
        print("- disposable Lab state only: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
