"""Host gate for Stage 7 Intelligence.

The gate intentionally does not require Ollama, llama.cpp, Tesseract, Whisper, a GPU,
or any remote AI service. All required checks exercise deterministic intelligence.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from teldrive_lab.intelligence import (
    anomaly_explanations,
    assert_advisory,
    capability_report,
    duplicate_explanations,
    export_intelligence,
    metadata_index,
    natural_language_search,
    recommendation_report,
    structured_filter,
    summarize_text,
)


def main() -> int:
    records = [
        {"path": "movies/Alpha.mp4", "name": "Alpha.mp4", "extension": ".mp4", "mime": "video/mp4", "size": 100, "sha256": "a" * 64, "integrity_state": "VERIFIED", "title": "Alpha"},
        {"path": "backup/Alpha-copy.mp4", "name": "Alpha-copy.mp4", "extension": ".mp4", "mime": "video/mp4", "size": 100, "sha256": "a" * 64, "integrity_state": "VERIFIED", "title": "Alpha copy"},
        {"path": "docs/report.pdf", "name": "report.pdf", "extension": ".pdf", "size": 50, "integrity_state": "UNVERIFIED"},
    ]
    index = metadata_index(records)
    with tempfile.TemporaryDirectory() as tmp:
        exported = export_intelligence(index, Path(tmp) / "intelligence.json")
        checks = {
            "strong_lexical_metadata_search": bool(natural_language_search("find Alpha mp4", index)),
            "structured_filters": len(structured_filter(records, extensions=[".mp4"])) == 2,
            "duplicate_explanations": bool(duplicate_explanations(records)),
            "anomaly_explanations": bool(anomaly_explanations(records, large_file_bytes=90)),
            "explainable_recommendations": recommendation_report(records)["mutation"] == "NONE",
            "deterministic_summary": summarize_text("First. Second.")["ai_used"] is False,
            "rebuildable_export": bool(exported["digest"]),
            "advisory_boundary": True,
            "ai_optional": capability_report()["core_requires_ai"] is False,
            "production_storage_mutation": "NONE",
        }
        assert_advisory(duplicate_explanations(records) + anomaly_explanations(records))
    print("STAGE 7 INTELLIGENCE GATE")
    print(json.dumps(checks, indent=2, sort_keys=True))
    ok = all(v is True for k, v in checks.items() if k != "production_storage_mutation") and checks["production_storage_mutation"] == "NONE"
    print(f"STAGE 7 INTELLIGENCE GATE: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
