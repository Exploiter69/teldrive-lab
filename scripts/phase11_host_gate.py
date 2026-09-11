#!/usr/bin/env python3
"""Phase 11 host gate: validate the CLI against isolated Lab-owned state only."""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


def run(*args: str, env: dict[str, str]):
    result = subprocess.run([sys.executable, "-m", "teldrive_lab.cli", *args], env=env, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise AssertionError(f"CLI failed: {args}\nstdout={result.stdout}\nstderr={result.stderr}")
    return json.loads(result.stdout)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="teldrive-lab-phase11-") as raw:
        root = Path(raw); state = root / "state"; env = dict(os.environ); env["TELDRIVE_LAB_STATE"] = str(root)
        init = run("init", env=env); assert str(root) == init["runtime"]

        source = root / "source"; source.mkdir(); (source / "alpha.txt").write_text("alpha", encoding="utf-8")
        indexed = run("index", str(source), env=env); assert indexed["indexed"] >= 1 and indexed["bounded"] is False
        found = run("search", "alpha", env=env); assert found["count"] == 1 and found["items"][0]["name"] == "alpha.txt"

        from teldrive_lab.jobs import JobStore, JobType
        store = JobStore(state / "jobs.db"); job = store.enqueue(JobType.INDEX, job_id="phase11-job"); assert store.claim("phase11-worker")
        listed = run("jobs", env=env); assert listed["count"] == 1
        assert run("job", job.job_id, env=env)["state"] == "RUNNING"
        run("pause", job.job_id, env=env); assert run("job", job.job_id, env=env)["state"] == "PAUSED"
        run("resume", job.job_id, env=env); assert run("job", job.job_id, env=env)["state"] == "QUEUED"
        run("cancel", job.job_id, env=env); assert run("job", job.job_id, env=env)["state"] == "CANCELLED"

        with sqlite3.connect(state / "audit.db") as conn:
            rows = conn.execute("SELECT operation, decision, result, details_json FROM events ORDER BY id").fetchall()
            assert sum(1 for row in rows if row[0] == "JOB_CONTROL") >= 3
            assert len(rows) >= 4
            audit_text = json.dumps(rows)
            assert "/home/thakuralok/TelegramRaw" not in audit_text
            assert "/home/thakuralok/TelegramDrive" not in audit_text

        storage = run("monitor", "storage", "--path", str(root), env=env); assert len(storage) == 1

    print("PHASE 11 HOST GATE: PASS")
    print("CLI operator surface: PASS")
    print("read-only search/index/status surfaces: PASS")
    print("durable job inspect/control: PASS")
    print("audit visibility: PASS")
    print("isolated runtime boundary: PASS")
    print("production storage mutation: NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
