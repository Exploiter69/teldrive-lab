"""R6 release-hardening gate: static safety and release-contract checks."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> int:
    roadmap = read("ROADMAP.md")
    checklist = read("docs/RELEASE_CHECKLIST.md")
    workflow = read(".github/workflows/test.yml")
    pyproject = read("pyproject.toml")
    boundary = read("PRODUCTION_BOUNDARY.md")
    safety = read("SAFETY_CONTRACT.md")

    # R6 must not silently regress the zero-cost/runtime contract.
    assert "dependencies = []" in pyproject
    assert "permissions:\n  contents: read" in workflow
    assert "timeout-minutes:" in workflow

    # Release documentation must identify R6 as the final hardening gate.
    assert "R6" in checklist
    assert "R6" in roadmap
    assert "R6" in boundary and "R6" in safety

    # Production-boundary language must remain explicit.
    required_safety_terms = (
        "TelDrive",
        "PostgreSQL",
        "protected",
        "authorization",
        "verification",
        "audit",
    )
    for term in required_safety_terms:
        assert term.lower() in (boundary + safety).lower(), term

    # Reject obvious unsafe execution patterns in Lab Python sources/scripts.
    source_files = list((ROOT / "teldrive_lab").rglob("*.py")) + list(
        (ROOT / "scripts").rglob("*.py")
    )
    forbidden = (
        r"os\.system\s*\(",
        r"subprocess\.(?:run|Popen|call|check_call|check_output)\([^\n]*shell\s*=\s*True",
    )
    for path in source_files:
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden:
            assert not re.search(pattern, text), f"unsafe execution pattern: {path}: {pattern}"

    # CI must execute the complete reconciliation matrix.
    for gate in (
        "r0_product_truth_gate.py",
        "r1_corpus_discovery_gate.py",
        "r2_unified_search_gate.py",
        "r3_media_jellyfin_gate.py",
        "r4_durable_execution_gate.py",
        "r5_control_center_gate.py",
        "phase4_host_gate.py",
        "phase5_host_gate.py",
        "phase6_host_gate.py",
        "phase7_host_gate.py",
        "phase8_host_gate.py",
        "phase9_host_gate.py",
        "phase10_host_gate.py",
        "phase11_host_gate.py",
        "phases12_22_host_gate.py",
    ):
        assert gate in workflow, gate

    # The release checklist must not claim the RC is ready merely from this gate.
    assert "Only then may an RC or release tag be created." in checklist

    print("R6 RELEASE HARDENING GATE: PASS")
    print("- zero-cost runtime contract: PASS")
    print("- least-privilege CI + bounded timeout: PASS")
    print("- production-boundary contract: PASS")
    print("- unsafe shell execution scan: PASS")
    print("- complete R0-R5/legacy CI matrix present: PASS")
    print("- release claims remain evidence-controlled: PASS")
    print("- no production TelDrive/rclone mutation performed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
