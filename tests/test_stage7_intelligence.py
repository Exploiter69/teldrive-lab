from pathlib import Path

from teldrive_lab.intelligence import (
    anomaly_explanations,
    assert_advisory,
    capability_report,
    duplicate_explanations,
    export_intelligence,
    metadata_enrichment_suggestions,
    metadata_index,
    natural_language_search,
    organization_suggestions,
    recommendation_report,
    structured_filter,
    summarize_text,
)


def records():
    return [
        {"path": "movies/Alpha.mp4", "name": "Alpha.mp4", "extension": ".mp4", "mime": "video/mp4", "size": 100, "sha256": "a" * 64, "integrity_state": "VERIFIED", "title": "Alpha"},
        {"path": "backup/Alpha-copy.mp4", "name": "Alpha-copy.mp4", "extension": ".mp4", "mime": "video/mp4", "size": 100, "sha256": "a" * 64, "integrity_state": "VERIFIED", "title": "Alpha copy"},
        {"path": "docs/report.pdf", "name": "report.pdf", "extension": ".pdf", "size": 50, "integrity_state": "UNVERIFIED"},
    ]


def test_strong_metadata_search_and_filters():
    index = metadata_index(records())
    results = natural_language_search("find Alpha mp4", index)
    assert results and results[0]["path"] == "movies/Alpha.mp4"
    filtered = structured_filter(records(), extensions=[".mp4"], min_size=100)
    assert [r["path"] for r in filtered] == ["backup/Alpha-copy.mp4", "movies/Alpha.mp4"]


def test_duplicate_and_anomaly_explanations_are_advisory():
    duplicates = duplicate_explanations(records())
    anomalies = anomaly_explanations(records(), large_file_bytes=90)
    assert duplicates and anomalies
    assert_advisory(duplicates + anomalies)


def test_recommendations_and_enrichment_are_non_authoritative():
    recs = recommendation_report(records())
    assert recs["mutation"] == "NONE"
    assert metadata_enrichment_suggestions(records())
    assert organization_suggestions(records())
    assert all(not r["authoritative"] for r in recs["recommendations"])


def test_deterministic_summary_uses_no_ai():
    result = summarize_text("First sentence. Second sentence. Third sentence.")
    assert result["ai_used"] is False
    assert result["summary"] == "First sentence. Second sentence. Third sentence."


def test_capability_report_does_not_require_ai():
    assert capability_report()["core_requires_ai"] is False


def test_export_is_rebuildable(tmp_path: Path):
    destination = tmp_path / "intelligence.json"
    result = export_intelligence(metadata_index(records()), destination)
    assert destination.exists()
    assert result["schema"] == "teldrive-lab.intelligence.v1"
    assert result["digest"]
