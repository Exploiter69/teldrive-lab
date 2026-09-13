"""Compatibility facade for the canonical Phase 12-22 implementation.

New code should import from :mod:`teldrive_lab.advanced`. Legacy names remain
available here while filesystem work delegates to bounded/streaming primitives.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from . import advanced
from .resources import DEFAULT_MAX_DEPTH, DEFAULT_MAX_FILES, DEFAULT_SAMPLE_BYTES, iter_files, stream_sha256


@dataclass(frozen=True)
class StorageObservation:
    path: str
    size: int
    atime: float
    mtime: float
    hot_score: float
    tier: str


def observe_storage(root: str | Path, *, now: float | None = None, hot_days: int = 30, cold_days: int = 180, max_depth: int = DEFAULT_MAX_DEPTH, max_files: int = DEFAULT_MAX_FILES) -> list[StorageObservation]:
    base = Path(root).expanduser().resolve(); current = now or time.time(); out = []
    for p in iter_files(base, max_depth=max_depth, max_files=max_files):
        st = p.stat(); age = max(0.0, current - max(st.st_atime, st.st_mtime)); days = age / 86400; score = max(0.0, 1.0 - days / max(hot_days, 1)); tier = "hot" if days <= hot_days else "warm" if days <= cold_days else "cold"
        out.append(StorageObservation(p.relative_to(base).as_posix(), st.st_size, st.st_atime, st.st_mtime, round(score, 6), tier))
    return out


def cache_pressure(cache_root: str | Path, capacity_bytes: int, *, max_depth: int = DEFAULT_MAX_DEPTH, max_files: int = DEFAULT_MAX_FILES) -> dict[str, int | float]:
    result = advanced.cache_pressure(Path(cache_root).expanduser(), capacity_bytes, max_depth=max_depth, max_files=max_files)
    return {"used_bytes": result["used_bytes"], "capacity_bytes": result["capacity_bytes"], "pressure": round(float(result["ratio"]), 6), "eviction_allowed": False}


def concurrency_budget(*, ram_available_mb: int, per_worker_mb: int = 256, cpu_count: int | None = None, max_workers: int = 4) -> int:
    return advanced.resource_budget(ram_available_mb, per_worker_mb, cpu_count, max_workers)


def cache_eviction_plan(observations: Iterable[StorageObservation], *, target_bytes: int) -> dict:
    heat = [advanced.StorageHeat(x.path, x.size, 0, x.mtime, x.tier, x.hot_score) for x in observations]
    result = advanced.eviction_plan(heat, target_bytes)
    return result | {"selected_bytes": result["planned_bytes"]}


def _now() -> str: return datetime.now(timezone.utc).isoformat()


def export_catalog_metadata(db_path: str | Path, output: str | Path) -> Path:
    db = Path(db_path); dest = Path(output); dest.parent.mkdir(parents=True, exist_ok=True); conn = sqlite3.connect(db); conn.row_factory = sqlite3.Row
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    payload = {"schema": 1, "exported_at": _now(), "tables": {}}
    for table in tables: payload["tables"][table] = [dict(r) for r in conn.execute(f'SELECT * FROM "{table}"').fetchall()]
    conn.close(); dest.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"); return dest


def validate_catalog_export(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8")); tables = data.get("tables"); valid = isinstance(tables, dict) and data.get("schema") == 1
    return {"valid": valid, "schema": data.get("schema"), "tables": sorted(tables) if isinstance(tables, dict) else []}


@dataclass(frozen=True)
class MediaRecord:
    path: str
    mime: str
    extension: str
    size: int
    duration_seconds: float | None = None


def scan_media(root: str | Path, *, max_depth: int = DEFAULT_MAX_DEPTH, max_files: int = DEFAULT_MAX_FILES) -> list[MediaRecord]:
    records = advanced.media_records(Path(root).expanduser().resolve(), max_depth=max_depth, max_files=max_files)
    return [MediaRecord(x["path"], x["mime"] or "application/octet-stream", x["extension"], x["size"]) for x in records]


def media_library_manifest(records: Iterable[MediaRecord]) -> dict:
    items = [asdict(x) for x in records]; return {"schema": 1, "count": len(items), "bytes": sum(x["size"] for x in items), "items": items, "sidecar_only": True}


def extract_text(path: str | Path, *, max_bytes: int = DEFAULT_SAMPLE_BYTES) -> str: return advanced.text_extract(Path(path), max_bytes=max_bytes)


def document_fingerprint(path: str | Path) -> dict:
    p = Path(path); result = advanced.document_fingerprint(p); text = extract_text(p); normalized = re.sub(r"\s+", " ", text).strip().lower(); result.update({"path": str(p), "bytes": result["size"], "text_sha256": hashlib.sha256(normalized.encode()).hexdigest() if text else None}); return result


def content_search(paths: Iterable[str | Path], query: str, *, limit: int = 50, max_bytes: int = DEFAULT_SAMPLE_BYTES) -> list[dict]:
    return advanced.search_content(advanced.content_index([Path(p) for p in paths], max_bytes=max_bytes), query, limit)


@dataclass(frozen=True)
class Advisory:
    kind: str
    confidence: float
    reason: str
    proposed_action: str
    authoritative: bool = False


def local_ai_advisory(text: str, *, context: str = "") -> Advisory:
    lowered = (text + " " + context).casefold()
    if any(x in lowered for x in ("password", "token", "secret", "private key")): return Advisory("security", .99, "sensitive-looking content detected", "do not index or export secrets")
    if "duplicate" in lowered: return Advisory("duplicate", .70, "duplicate-related language detected", "review duplicate report")
    return Advisory("general", .20, "no deterministic high-confidence signal", "no automatic action")


def advisory_contract(advisory: Advisory) -> dict: return {"advisory": asdict(advisory), "policy_required": True, "authorization_required": True, "verification_required": True, "audit_required": True}


def storage_economics(observations: Iterable[StorageObservation], *, duplicate_bytes: int = 0) -> dict:
    items = list(observations); tiers = {t: sum(x.size for x in items if x.tier == t) for t in ("hot", "warm", "cold")}; return {"total_bytes": sum(x.size for x in items), "file_count": len(items), "hot_bytes": tiers["hot"], "warm_bytes": tiers["warm"], "cold_bytes": tiers["cold"], "duplicate_bytes": max(0, duplicate_bytes), "reclaimable_estimate": max(0, duplicate_bytes), "recommendations": ["review cold data before any transfer"] if tiers["cold"] else []}


def growth_forecast(samples: Iterable[tuple[float, int]]) -> dict: return advanced.growth_forecast(samples)


def create_snapshot_manifest(root: str | Path, output: str | Path, *, max_depth: int = DEFAULT_MAX_DEPTH, max_files: int = DEFAULT_MAX_FILES) -> Path:
    base = Path(root).expanduser().resolve(); dest = Path(output); dest.parent.mkdir(parents=True, exist_ok=True); entries = []
    for p in iter_files(base, max_depth=max_depth, max_files=max_files):
        digest, size = stream_sha256(p); entries.append({"relative_path": p.relative_to(base).as_posix(), "size": size, "sha256": digest})
    payload = {"schema": 1, "created_at": _now(), "root": str(base), "entries": entries}; payload["digest"] = hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest(); dest.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"); return dest


def verify_snapshot_manifest(manifest: str | Path, root: str | Path, *, max_depth: int = DEFAULT_MAX_DEPTH, max_files: int = DEFAULT_MAX_FILES) -> dict:
    data = json.loads(Path(manifest).read_text(encoding="utf-8")); base = Path(root).expanduser().resolve(); actual = {p.relative_to(base).as_posix(): p for p in iter_files(base, max_depth=max_depth, max_files=max_files)}; missing = []; changed = []
    for item in data.get("entries", []):
        p = actual.get(item["relative_path"])
        if p is None: missing.append(item["relative_path"]); continue
        digest, size = stream_sha256(p)
        if size != item["size"] or digest != item["sha256"]: changed.append(item["relative_path"])
    return {"verified": not missing and not changed, "missing": missing, "changed": changed, "entry_count": len(data.get("entries", []))}


@dataclass(frozen=True)
class IntegrationContract:
    name: str
    version: str
    operations: tuple[str, ...]
    production_write: bool = False
    authorization_required: bool = True


def integration_contracts() -> list[IntegrationContract]: return [IntegrationContract("vajra", "1", ("catalog.read", "plan.read", "audit.read")), IntegrationContract("engineering-lab", "1", ("catalog.read", "archive.plan", "snapshot.read")), IntegrationContract("dataset-workflow", "1", ("catalog.read", "integrity.read", "export.metadata"))]

@dataclass(frozen=True)
class ExperimentSpec:
    name: str
    description: str
    isolation: str = "lab-owned-only"
    production_mutation: bool = False


def experimental_registry() -> list[ExperimentSpec]: return [ExperimentSpec("content-addressable-index", "benchmark content-addressed metadata without moving files"), ExperimentSpec("tiering-simulator", "simulate tier placement and costs without changing storage"), ExperimentSpec("snapshot-compression-benchmark", "measure local compression on copied test fixtures"), ExperimentSpec("distributed-worker-protocol", "protocol-only worker leasing experiment")]


def control_center_payload(root: str | Path) -> dict:
    observations = observe_storage(root); return {"schema": 1, "generated_at": _now(), "storage": storage_economics(observations), "cache": cache_pressure(Path(root) / "cache", 1), "integrations": [asdict(x) for x in integration_contracts()], "experiments": [asdict(x) for x in experimental_registry()], "authority": "teldrive", "ui_mutation_policy": "none"}


def validate_extended_safety() -> dict: return {"production_write": False, "production_delete": False, "automatic_eviction": False, "telldrive_db_write": False, "ai_authority": False, "all_mutations_require_explicit_authorization": True}


# Direct aliases for canonical symbols used by legacy callers.
StorageHeat = advanced.StorageHeat
storage_tier = advanced.storage_tier
storage_heatmap = advanced.storage_heatmap
prefetch_suggestions = advanced.prefetch_suggestions
record_access = advanced.record_access
access_frequency = advanced.access_frequency
resource_budget = advanced.resource_budget
export_metadata = advanced.export_metadata
validate_metadata_export = advanced.validate_metadata_export
import_metadata = advanced.import_metadata
filesystem_metadata_view = advanced.filesystem_metadata_view
serve_json_api = advanced.serve_json_api
validate_loopback_host = advanced.validate_loopback_host
media_records = advanced.media_records
subtitle_index = advanced.subtitle_index
media_probe = advanced.media_probe
thumbnail_capability = advanced.thumbnail_capability
media_integrations = advanced.media_integrations
remote_metadata_request = advanced.remote_metadata_request
text_extract = advanced.text_extract
pdf_metadata = advanced.pdf_metadata
ocr = advanced.ocr
local_embedding = advanced.local_embedding
image_vision_summary = advanced.image_vision_summary
content_index = advanced.content_index
search_content = advanced.search_content
AIProposal = advanced.AIProposal
ai_proposal = advanced.ai_proposal
natural_language_search = advanced.natural_language_search
organization_suggestions = advanced.organization_suggestions
anomaly_explanations = advanced.anomaly_explanations
category_analysis = advanced.category_analysis
transfer_cost_estimate = advanced.transfer_cost_estimate
manifest_tree = advanced.manifest_tree
create_snapshot = advanced.create_snapshot
verify_snapshot = advanced.verify_snapshot
retention_plan = advanced.retention_plan
restore_plan = advanced.restore_plan
ProjectContract = advanced.ProjectContract
project_contracts = advanced.project_contracts
validate_project_request = advanced.validate_project_request
CASStore = advanced.CASStore
dedup_plan = advanced.dedup_plan
tiering_plan = advanced.tiering_plan
compressed_snapshot = advanced.compressed_snapshot
WorkerNode = advanced.WorkerNode
worker_registry = advanced.worker_registry
dispatch_plan = advanced.dispatch_plan
ai_workflow_plan = advanced.ai_workflow_plan
extended_safety = advanced.extended_safety
control_center_server = advanced.control_center_server

__all__ = [name for name in globals() if not name.startswith("_")]
