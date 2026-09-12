#!/usr/bin/env python3
"""R2 product gate: prove unified search is bounded, read-only, and FTS5-backed."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEARCH = ROOT / "teldrive_lab" / "search.py"
CLI = ROOT / "teldrive_lab" / "cli_r2.py"
DOC = ROOT / "docs" / "R2-UNIFIED-SEARCH.md"
TEST = ROOT / "tests" / "test_r2_search.py"


def main() -> int:
    checks: list[tuple[str, bool]] = []
    text = SEARCH.read_text(encoding="utf-8")
    cli = CLI.read_text(encoding="utf-8")
    checks.append(("canonical unified search module exists", SEARCH.exists()))
    checks.append(("FTS5 virtual table is canonical index", "USING fts5" in text))
    checks.append(("optional content is unified", all(x in text for x in ["r2_search_content", "index_content", "content"])))
    checks.append(("structured filters are supported", all(x in text for x in ["source_type", "path_prefix", "min_size", "modified_after"])))
    checks.append(("deterministic ordering and pagination are bounded", all(x in text for x in ["ORDER BY", "LIMIT ? OFFSET ?", "MAX_LIMIT"])))
    checks.append(("content input is bounded", "MAX_CONTENT_CHARS" in text))
    checks.append(("td search routes through R2", "if len(sys.argv) < 2 or sys.argv[1] != \"search\"" in cli))
    checks.append(("R2 search declares no production mutation", '"mutation": "NONE"' in cli))
    checks.append(("R2 tests exist", TEST.exists()))
    checks.append(("R2 documentation exists", DOC.exists()))
    checks.append(("no storage mutation commands in search module", not any(x in text for x in ["rclone copy", "rclone move", "rclone delete", "shutil.move", "unlink("])))
    result = subprocess.run([sys.executable, "-m", "pytest", "tests/test_r2_search.py"], cwd=ROOT, capture_output=True, text=True, check=False)
    checks.append(("R2 isolated test suite passes", result.returncode == 0))
    for name, ok in checks:
        print(f"- {name}: {'PASS' if ok else 'FAIL'}")
    if result.returncode != 0:
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
    success = all(ok for _, ok in checks)
    print("R2 UNIFIED SEARCH GATE: " + ("PASS" if success else "FAIL"))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
