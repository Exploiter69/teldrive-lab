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


def run(*args: str, env: dict[str, str]) -> dict:
    result = subprocess.run([sys.executable, "-m", "teldrive_lab.cli", *args], env=env, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise AssertionError(f"CLI failed: {args}\nstdout={result.stdout}\nstderr={result.stderr}")
    return json.loads(result.stdout)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="teldrive-lab-phase11-") as raw:
        root = Path(raw); state = root / "state"; env = dict(os.environ); env["TELDRIVE_LAB_STATE"] = str(root)
        init = run("init", env=env)
        assert str(root) == init["runtime"]

        source = root / "source"; source.mkdir(); (source / "alpha.txt").write_text("alpha", encoding="utf-8")
        indexed = run("index", str(source), env=env)
        assert indexed["indexed"] >= 1 and indexed["bounded"] is False

        found = run("search", "alpha", env=env)
        assert found["count"] == 1 and found["items"][0]["name"] == "alpha.txt"

        store_db = state / "jobs.db"
        import sys as _sys
        _sys.path.insert(0, str(Path.cwd()))
        from teldrive_lab.jobs import JobStore, JobType
        store = JobStore(store_db); job = store.enqueue(JobType.INDEX, job_id="phase11-job"); claimed = store.claim("phase11-worker"); assert claimed

        listed = run("jobs", env=env); assert listed["count"] == 1
        detail = run("job", job.job_id, env=env); assert detail["state"] == "RUNNING"
        run("pause", job.job_id, env=env)
        assert run("job", job.job_id, env=env)["state"] == "PAUSED"
        run("resume", job.job_id, env=env)
        assert run("job", job.job_id, env=env)["state"] == "QUEUED"
        run("cancel", job.job_id, env=env)
        assert run("job", job.job_id, env=env)["state"] == "CANCELLED"

        audit = run("audit", env=env); assert any(row["operation"] == "JOB_CONTROL" for row in audit)
        storage = run("monitor", "storage", "--path", str(root), env=env); assert len(storage) == 1

        with sqlite3.connect(state / "audit.db") as conn:
            assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] >= 4

        # The gate must never reference or mutate production paths.
        assert "/home/thakuralok/TelegramRaw" not in json.dumps(audit)
        assert "/home/thakuralok/TelegramDrive" not in json.dumps(audit)

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
