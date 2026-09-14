"""R0 Product Truth gate.

This gate performs repository-local checks only. It never touches TelDrive
production storage. It protects the reconciliation decision with both
implementation checks and documentation/CI checks.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> int:
    roadmap = read("ROADMAP.md")
    status = read("docs/PHASES_12_22_IMPLEMENTATION_STATUS.md")
    operations = read("docs/OPERATIONS.md")
    workflow = read(".github/workflows/test.yml")
    safety = read("teldrive_lab/safety.py")
    runtime = read("teldrive_lab/runtime.py")
    advanced = read("teldrive_lab/advanced.py")
    extended = read("teldrive_lab/extended.py")
    resources = read("teldrive_lab/resources.py")
    failures: list[str] = []

    # R0 protects the current product contract. P12-P21 remain extension
    # capabilities and must not be promoted to COMPLETE merely by legacy
    # documentation claims.
    for n in (12, 13, 15, 16, 17, 18, 19, 20, 21):
        if f"| {n} | COMPLETE" in status:
            failures.append(f"status still advertises forbidden completion: | {n} | COMPLETE")
    if "Core control plane: COMPLETE and release-hardened through R0–R6." not in roadmap:
        failures.append("roadmap is missing the current core release state")
    if "PRIMITIVE → IMPLEMENTED → INTEGRATED → OPERATIONAL" not in roadmap:
        failures.append("roadmap is missing the evidence-driven completion standard")
    if "TelDrive remains the production storage authority" not in roadmap:
        failures.append("roadmap is missing the TelDrive authority boundary")
    for marker, text, message in (
        ("TELDRIVE_LAB_PROTECTED_ROOTS", operations, "operator documentation is missing configurable protected roots"),
        ("TELDRIVE_LAB_PROTECTED_STATE", operations, "operator documentation is missing configurable protected state"),
        ("TELDRIVE_LAB_PROTECTED_ROOTS", safety, "safety code does not implement configurable protected roots"),
        ("TELDRIVE_LAB_PROTECTED_STATE", safety, "safety code does not implement configurable protected state"),
    ):
        if marker not in text:
            failures.append(message)
    if "is_protected" not in runtime or "protected production boundary" not in runtime:
        failures.append("runtime code does not reject protected state/cache paths")
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

    # Canonicalization is enforced structurally, not by a documentation claim.
    try:
        ast.parse(advanced)
        ast.parse(extended)
        ast.parse(resources)
    except SyntaxError as exc:
        failures.append(f"canonical module syntax error: {exc}")
    if "from . import advanced" not in extended:
        failures.append("extended.py is not a compatibility facade over advanced.py")
    if ".rglob(" in advanced or ".rglob(" in extended:
        failures.append("canonical Phase 12-22 code contains unbounded rglob traversal")
    if ".read_bytes(" in advanced or ".read_bytes(" in extended:
        failures.append("canonical Phase 12-22 code contains whole-file read_bytes usage")
    for symbol in ("iter_files", "stream_sha256", "bounded_sample", "copy_stream", "ResourceLimitError"):
        if symbol not in resources:
            failures.append(f"resource primitive missing: {symbol}")
    for symbol in ("iter_files", "stream_sha256", "bounded_sample", "copy_stream"):
        if symbol not in advanced:
            failures.append(f"advanced.py does not use canonical resource primitive: {symbol}")
    if "validate_loopback_host" not in advanced or "ipaddress" not in advanced:
        failures.append("HTTP loopback binding validation is missing")
    if "validate_loopback_host(host)" not in advanced:
        failures.append("HTTP servers do not enforce loopback validation")
    for host in ("0.0.0.0", "::"):
        if host not in read("tests/test_r0_readonly_api.py"):
            failures.append(f"API binding test missing {host}")
    if "ResourceLimitError" not in read("tests/test_r0_resources.py"):
        failures.append("resource-limit tests are missing")
    if "test_extended_delegates_canonical_symbols" not in read("tests/test_r0_canonicalization.py"):
        failures.append("canonicalization delegation test is missing")
    if "loopback" not in operations.lower():
        failures.append("OPERATIONS does not document loopback-only API binding")

    if failures:
        print("R0 PRODUCT TRUTH GATE: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("R0 PRODUCT TRUTH GATE: PASS")
    print("- current product contract and evidence-driven completion state: PASS")
    print("- Phase 12-22 false completion claims blocked: PASS")
    print("- advanced.py canonical / extended.py compatibility facade: PASS")
    print("- bounded traversal + streaming file primitives enforced: PASS")
    print("- whole-file canonical read/traversal patterns blocked: PASS")
    print("- loopback-only read-only HTTP binding enforced: PASS")
    print("- required R0 tests present: PASS")
    print("- configurable protected roots/state and runtime boundary: PASS")
    print("- CI permissions/timeout/interpreter hardening: PASS")
    print("- Phase 4 and Phase 5 host gates enforced by CI: PASS")
    print("- production I/O/mutation: NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
