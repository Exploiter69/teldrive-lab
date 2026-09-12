"""Static R0 reconciliation gate.

This gate checks that repository-level product claims remain aligned with the
R0 decision: incomplete capabilities must not be advertised as complete, the
CI workflow must enforce the safety chain, and the documented configurable
safety boundary must exist in code.

It deliberately performs no production I/O or mutation.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> int:
    roadmap = read("ROADMAP.md")
    status = read("docs/PHASES_12_22_IMPLEMENTATION_STATUS.md")
    reconciliation = read("docs/RECONCILIATION_GATE_R0.md")
    operations = read("docs/OPERATIONS.md")
    workflow = read(".github/workflows/test.yml")
    safety = read("teldrive_lab/safety.py")
    runtime = read("teldrive_lab/runtime.py")

    failures: list[str] = []

    # False completion claims are the primary R0 regression this gate protects.
    forbidden_status_rows = (
        "| 12 | COMPLETE",
        "| 13 | COMPLETE",
        "| 14 | COMPLETE",
        "| 15 | COMPLETE",
        "| 16 | COMPLETE",
        "| 17 | COMPLETE",
        "| 18 | COMPLETE",
        "| 19 | COMPLETE",
        "| 20 | COMPLETE",
        "| 21 | COMPLETE",
        "| 22 | COMPLETE",
    )
    for marker in forbidden_status_rows:
        if marker in status:
            failures.append(f"status still advertises forbidden completion: {marker}")

    if "**Status at R0:** PARTIAL, not COMPLETE." not in roadmap:
        failures.append("roadmap Phase 6 completion claim was not reconciled")
    if "R0 → R5" not in roadmap:
        failures.append("roadmap is missing the R0→R5 reconciliation program")
    if "PRIMITIVE → IMPLEMENTED → INTEGRATED → OPERATIONAL" not in roadmap:
        failures.append("roadmap is missing the evidence-driven completion standard")

    if "TELDRIVE_LAB_PROTECTED_ROOTS" not in operations:
        failures.append("operator documentation is missing configurable protected roots")
    if "TELDRIVE_LAB_PROTECTED_STATE" not in operations:
        failures.append("operator documentation is missing configurable protected state")
    if "TELDRIVE_LAB_PROTECTED_ROOTS" not in safety:
        failures.append("safety code does not implement configurable protected roots")
    if "TELDRIVE_LAB_PROTECTED_STATE" not in safety:
        failures.append("safety code does not implement configurable protected state")
    if "is_protected" not in runtime or "protected production boundary" not in runtime:
        failures.append("runtime code does not reject protected state/cache paths")

    # CI must exercise the actual early transfer/organization safety gates as
    # well as the later chain; pytest must use the configured interpreter.
    for command in (
        "python -m pytest",
        "python scripts/r0_product_truth_gate.py",
        "python scripts/phase4_host_gate.py",
        "python scripts/phase5_host_gate.py",
    ):
        if command not in workflow:
            failures.append(f"CI is missing required command: {command}")
    if "permissions:\n  contents: read" not in workflow:
        failures.append("CI does not declare least-privilege repository permissions")
    if "timeout-minutes:" not in workflow:
        failures.append("CI does not declare a bounded job timeout")

    if failures:
        print("R0 PRODUCT TRUTH GATE: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("R0 PRODUCT TRUTH GATE: PASS")
    print("- evidence-driven completion standard: PASS")
    print("- Phase 12–22 false completion claims blocked: PASS")
    print("- Phase 6 roadmap truth reconciled: PASS")
    print("- configurable protected roots/state implemented: PASS")
    print("- Lab runtime protected-boundary rejection present: PASS")
    print("- CI permissions/timeout/interpreter hardening present: PASS")
    print("- Phase 4 and Phase 5 host gates enforced by CI: PASS")
    print("- production I/O/mutation: NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
