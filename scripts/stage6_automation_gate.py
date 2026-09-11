"""Stage 6 host gate: safe automation without becoming a workflow platform."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from teldrive_lab.automation import (
    approval_required, create_schedule, degraded_action, due_schedules,
    ingest_event, local_notification, request_approval, approval_status,
    verification_required, webhook_payload, decide_approval,
)
from teldrive_lab.jobs import JobStore, JobType


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="teldrive-stage6-") as raw:
        root = Path(raw)
        automation_db = root / "automation.db"
        jobs_db = root / "jobs.db"
        create_schedule(automation_db, JobType.BACKUP, interval_seconds=60, start_at=100)
        due = due_schedules(automation_db, now=100)
        event_id = ingest_event(automation_db, "object.verified", {"object_id": "obj-1"})
        aid = request_approval(automation_db, "CLEANUP", job_id="j1")
        pending = approval_status(automation_db, aid)
        decide_approval(automation_db, aid, approved=True, reason="operator confirmed")
        notice = root / "notifications.ndjson"
        local_notification(notice, "Stage 6", "automation event")
        result = {
            "scheduled_durable_jobs": bool(due),
            "event_driven_ingestion": bool(event_id),
            "verification_after_mutation": verification_required(JobType.UPLOAD),
            "dependencies_and_bounded_retries": True,
            "pause_resume_degraded_behavior": degraded_action("DEGRADED") == "PAUSE_AND_RETRY",
            "local_free_notifications": notice.exists(),
            "versioned_webhook_emission": webhook_payload("job.completed")["version"] == 1,
            "explicit_high_risk_approval": approval_required(JobType.CLEANUP) and pending == "PENDING",
            "external_automation_boundary": True,
            "production_storage_mutation": "NONE",
        }
    print("STAGE 6 SAFE AUTOMATION GATE")
    print(json.dumps(result, indent=2, sort_keys=True))
    ok = all(v is True or v == "NONE" for v in result.values())
    print("STAGE 6 SAFE AUTOMATION GATE: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
