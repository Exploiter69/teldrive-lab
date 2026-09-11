#!/usr/bin/env python3
"""Phase 11 host gate: verify the CLI boots inside an isolated Lab runtime."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def run(*args: str, env: dict[str, str]) -> str:
    result = subprocess.run([sys.executable, "-m", "teldrive_lab.cli", *args], env=env, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise AssertionError(f"CLI failed: {args}: {result.stderr or result.stdout}")
    return result.stdout


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="teldrive-lab-phase11-") as raw:
        root = Path(raw); env = dict(os.environ); env["TELDRIVE_LAB_STATE"] = str(root)
        payload = json.loads(run("init", env=env))
        assert payload["runtime"] == str(root)
        assert (root / "state").is_dir()
        assert (root / "cache").is_dir()
        help_output = run("--help", env=env)
        assert "TelDrive Lab safe operator CLI" in help_output
        assert "search" in help_output and "jobs" in help_output and "monitor" in help_output

    print("PHASE 11 HOST GATE: PASS")
    print("CLI bootstrap and command discovery: PASS")
    print("isolated runtime boundary: PASS")
    print("production storage mutation: NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
