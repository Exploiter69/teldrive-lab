from pathlib import Path

import teldrive_lab.advanced as advanced
import teldrive_lab.extended as extended


def test_extended_delegates_canonical_symbols():
    assert extended.storage_tier is advanced.storage_tier
    assert extended.storage_heatmap is advanced.storage_heatmap
    assert extended.CASStore is advanced.CASStore
    assert extended.serve_json_api is advanced.serve_json_api
    assert extended.validate_loopback_host is advanced.validate_loopback_host


def test_canonical_modules_have_no_unbounded_filesystem_patterns():
    root = Path(__file__).parents[1] / "teldrive_lab"
    advanced_source = (root / "advanced.py").read_text(encoding="utf-8")
    extended_source = (root / "extended.py").read_text(encoding="utf-8")
    assert ".rglob(" not in advanced_source
    assert ".rglob(" not in extended_source
    assert ".read_bytes(" not in advanced_source
    assert ".read_bytes(" not in extended_source
