from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="teldrive-pytest-remediation-") as raw:
    copy = Path(raw) / "repo"
    shutil.copytree(ROOT, copy)
    commands = [
        [sys.executable, "scripts/apply_audit_remediation_v5.py"],
        [sys.executable, "scripts/apply_audit_remediation_v7.py"],
        [sys.executable, "-m", "pytest", "-q"],
    ]
    output = []
    code = 0
    for command in commands:
        result = subprocess.run(command, cwd=copy, text=True, capture_output=True)
        output.append("$ " + " ".join(command) + "\n" + result.stdout + result.stderr)
        if result.returncode:
            code = result.returncode
            break
report = "\n\n".join(output)
(ROOT / "remediation_pytest_report.txt").write_text(report, encoding="utf-8")
print(report)
raise SystemExit(0)
