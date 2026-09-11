from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="teldrive-remediation-") as raw:
    copy = Path(raw) / "repo"
    shutil.copytree(ROOT, copy)
    result = subprocess.run(
        [sys.executable, "scripts/apply_audit_remediation_v2.py"],
        cwd=copy,
        text=True,
        capture_output=True,
    )
    report = "returncode=" + str(result.returncode) + "\nSTDOUT:\n" + result.stdout + "\nSTDERR:\n" + result.stderr
(ROOT / "remediation_v2_execution_report.txt").write_text(report, encoding="utf-8")
print(report)
raise SystemExit(0)
