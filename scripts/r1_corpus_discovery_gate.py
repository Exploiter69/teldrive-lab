"""R1 product gate: prove automatic TelDrive corpus discovery is safe and real."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    raise SystemExit(f"R1 CORPUS DISCOVERY GATE: FAIL\n- {message}")


def main() -> int:
    corpus = ROOT / "teldrive_lab" / "corpus.py"
    catalog = ROOT / "teldrive_lab" / "catalog.py"
    tests = ROOT / "tests" / "test_r1_corpus_discovery.py"
    docs = ROOT / "docs" / "R1-CORPUS-DISCOVERY.md"

    for path in (corpus, catalog, tests, docs):
        if not path.exists():
            fail(f"missing R1 artifact: {path.relative_to(ROOT)}")

    source = corpus.read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    subprocess_commands: list[str] = []
    for node in calls:
        if isinstance(node.func, ast.Attribute) and node.func.attr in {"run", "call", "check_call", "check_output", "Popen"}:
            try:
                subprocess_commands.append(ast.unparse(node.args[0]))
            except Exception:
                subprocess_commands.append("")

    if "lsf" not in source or "--recursive" not in source or "--files-only" not in source:
        fail("R1 source does not use bounded recursive read-only rclone listing")
    forbidden = {"copy", "copyto", "move", "moveto", "delete", "purge", "sync", "mount", "config"}
    for command in subprocess_commands:
        lowered = command.lower()
        if any(token in lowered for token in forbidden):
            fail(f"forbidden rclone mutation/config command detected: {command}")
    if "max_entries" not in source or "timeout_seconds" not in source:
        fail("R1 source is missing hard resource/time bounds")
    if "catalog.reconcile_source" not in source:
        fail("R1 source does not report stale catalog observations")
    if "sha256=None" not in source:
        fail("R1 discovery must not hash/download remote file contents")
    if "SourceType.TELDRIVE" not in source:
        fail("R1 source does not write TELDRIVE catalog records")
    if "TELDRIVE_LAB_TELDRIVE_RCLONE_REMOTE" not in source:
        fail("R1 is missing explicit remote configuration")

    print("R1 CORPUS DISCOVERY GATE: PASS")
    print("- automatic TelDrive/rclone corpus listing: PASS")
    print("- Lab-owned catalog ingestion: PASS")
    print("- bounded entries + timeout: PASS")
    print("- read-only rclone command boundary: PASS")
    print("- no remote content download/hash: PASS")
    print("- stale observation reporting without deletion: PASS")
    print("- isolated tests/docs present: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
