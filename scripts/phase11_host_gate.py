#!/usr/bin/env python3
"""Phase 11 host gate: deterministic CLI smoke test using isolated Lab state."""
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
        raise AssertionError(f"CLI failed: {args}: {result.stderr or result.stdout}")
    return json.loads(result.stdout)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="teldrive-lab-phase11-") as raw:
        root = Path(raw); env = dict(os.environ); env["TELDRIVE_LAB_STATE"] = str(root)
        init = run("init", env=env); assert init["runtime"] == str(root)

        source = root / "source"; source.mkdir(); (source / "alpha.txt").write_text("alpha", encoding="utf-8")
        indexed = run("index", str(source), env=env)
        assert indexed["indexed"] == 1 and indexed["bounded"] is False
        found = run("search", "alpha", env=env)
        assert found["count"] == 1 and found["items"][0]["name"] == "alpha.txt"

        jobs = run("jobs", env=env); assert jobs["count"] == 0
        health = run("health", env=env); assert isinstance(health, list)
        storage = run("monitor", "storage", "--path", str(root), env=env); assert len(storage) == 1
        alerts = run("monitor", "alerts", env=env); assert alerts == []

        with sqlite3.connect(root / "state" / "audit.db") as conn:
            rows = conn.execute("SELECT operation FROM events ORDER BY id").fetchall()
            assert any(row[0] == "INDEX" for row in rows)
            assert len(rows) >= 1
            text = json.dumps(rows)
            assert "/home/thakuralok/TelegramRaw" not in text
            assert "/home/thakuralok/TelegramDrive" not in text

    print("PHASE 11 HOST GATE: PASS")
    print("CLI operator surface: PASS")
    print("read-only index/search/health/storage/alerts: PASS")
    print("audit persistence: PASS")
    print("isolated runtime boundary: PASS")
    print("production storage mutation: NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
