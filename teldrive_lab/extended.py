"""Post-core capabilities for TelDrive Lab (Phases 12-22).

This module deliberately implements the useful local, deterministic parts of the
advanced roadmap without taking ownership of TelDrive production storage. Every
operation produces plans/reports first; no production deletion, eviction, DB write,
or service reconfiguration is performed here.
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import shutil
import sqlite3
import statistics
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while data := fh.read(chunk): h.update(data)
    return h.hexdigest()


def _safe_relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


# Phase 12 -----------------------------------------------------------------
@dataclass(frozen=True)
class StorageObservation:
    path: str
    size: int
    atime: float
    mtime: float
    hot_score: float
    tier: str


def observe_storage(root: str | Path, *, now: float | None = None, hot_days: int = 30, cold_days: int = 180) -> list[StorageObservation]:
    """Classify files only; never evicts or changes them."""
    base = Path(root).expanduser().resolve(); current = now or time.time(); out = []
    for p in sorted((x for x in base.rglob("*") if x.is_file()), key=lambda x: x.as_posix()):
        st = p.stat(); age = max(0.0, current - max(st.st_atime, st.st_mtime)); days = age / 86400
        score = max(0.0, 1.0 - days / max(hot_days, 1))
        tier = "hot" if days <= hot_days else "warm" if days <= cold_days else "cold"
        out.append(StorageObservation(_safe_relative(base, p), st.st_size, st.st_atime, st.st_mtime, round(score, 6), tier))
    return out


def cache_pressure(cache_root: str | Path, capacity_bytes: int) -> dict[str, int | float]:
    base = Path(cache_root).expanduser(); used = sum(p.stat().st_size for p in base.rglob("*") if p.is_file()) if base.exists() else 0
    ratio = used / capacity_bytes if capacity_bytes > 0 else 0.0
    return {"used_bytes": used, "capacity_bytes": capacity_bytes, "pressure": round(ratio, 6), "eviction_allowed": False}


def concurrency_budget(*, ram_available_mb: int, per_worker_mb: int = 256, cpu_count: int | None = None, max_workers: int = 4) -> int:
    cpu = cpu_count or (os.cpu_count() or 1)
    return max(1, min(max_workers, cpu, max(1, ram_available_mb // max(per_worker_mb, 1))))


def cache_eviction_plan(observations: Iterable[StorageObservation], *, target_bytes: int) -> dict:
    """Advisory plan only; callers must explicitly authorize any cache-owned deletion."""
    ordered = sorted(observations, key=lambda x: (x.tier != "cold", x.atime, x.path))
    selected=[]; total=0
    for item in ordered:
        if total >= target_bytes: break
        selected.append(asdict(item)); total += item.size
    return {"target_bytes": target_bytes, "selected_bytes": total, "items": selected, "action": "PLAN_ONLY"}


# Phase 13 -----------------------------------------------------------------
def export_catalog_metadata(db_path: str | Path, output: str | Path) -> Path:
    """Export catalog tables as portable JSON; read-only against the source DB."""
    db = Path(db_path); dest = Path(output); dest.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db); conn.row_factory = sqlite3.Row
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    payload = {"schema": 1, "exported_at": _now(), "tables": {}}
    for table in tables:
        rows = conn.execute(f'SELECT * FROM "{table}"').fetchall()
        payload["tables"][table] = [dict(r) for r in rows]
    conn.close(); dest.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"); return dest


def validate_catalog_export(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8")); tables = data.get("tables")
    valid = isinstance(tables, dict) and data.get("schema") == 1
    return {"valid": valid, "schema": data.get("schema"), "tables": sorted(tables) if isinstance(tables, dict) else []}


# Phase 14 -----------------------------------------------------------------
@dataclass(frozen=True)
class MediaRecord:
    path: str
    mime: str
    extension: str
    size: int
    duration_seconds: float | None = None

_MEDIA = {".mp4",".mkv",".webm",".avi",".mov",".mp3",".flac",".m4a",".wav",".ogg",".jpg",".jpeg",".png",".webp",".gif"}

def scan_media(root: str | Path) -> list[MediaRecord]:
    base=Path(root).expanduser().resolve(); out=[]
    for p in sorted((x for x in base.rglob("*") if x.is_file() and x.suffix.lower() in _MEDIA), key=lambda x:x.as_posix()):
        out.append(MediaRecord(_safe_relative(base,p), mimetypes.guess_type(p.name)[0] or "application/octet-stream", p.suffix.lower(), p.stat().st_size))
    return out


def media_library_manifest(records: Iterable[MediaRecord]) -> dict:
    items=[asdict(x) for x in records]
    return {"schema":1,"count":len(items),"bytes":sum(x["size"] for x in items),"items":items,"sidecar_only":True}


# Phase 15 -----------------------------------------------------------------
_TEXT_EXT = {".txt",".md",".rst",".py",".js",".ts",".tsx",".jsx",".json",".yaml",".yml",".toml",".csv",".log",".srt"}

def extract_text(path: str | Path, *, max_bytes: int = 2_000_000) -> str:
    p=Path(path); data=p.read_bytes()[:max_bytes]
    return data.decode("utf-8", errors="replace") if p.suffix.lower() in _TEXT_EXT or p.name.lower().endswith(".md") else ""


def document_fingerprint(path: str | Path) -> dict:
    p=Path(path); text=extract_text(p); normalized=re.sub(r"\s+"," ",text).strip().lower()
    return {"path":str(p),"bytes":p.stat().st_size,"sha256":_sha256(p),"text_available":bool(text),"text_chars":len(text),"text_sha256":hashlib.sha256(normalized.encode()).hexdigest() if text else None}


# Phase 16 -----------------------------------------------------------------
def content_search(paths: Iterable[str | Path], query: str, *, limit: int = 50) -> list[dict]:
    q=query.casefold(); hits=[]
    for raw in paths:
        p=Path(raw)
        if not p.is_file(): continue
        text=extract_text(p)
        if q in text.casefold(): hits.append({"path":str(p),"score":round(text.casefold().count(q)/max(len(text),1),8),"matches":text.casefold().count(q)})
        if len(hits)>=limit: break
    return sorted(hits,key=lambda x:(-x["matches"],x["path"]))


# Phase 17 -----------------------------------------------------------------
@dataclass(frozen=True)
class Advisory:
    kind: str
    confidence: float
    reason: str
    proposed_action: str
    authoritative: bool = False


def local_ai_advisory(text: str, *, context: str = "") -> Advisory:
    """Deterministic fallback advisory; an external/local model can consume the same contract later."""
    lowered=(text+" "+context).casefold()
    if any(x in lowered for x in ("password", "token", "secret", "private key")):
        return Advisory("security",0.99,"sensitive-looking content detected","do not index or export secrets")
    if "duplicate" in lowered: return Advisory("duplicate",0.70,"duplicate-related language detected","review duplicate report")
    return Advisory("general",0.20,"no deterministic high-confidence signal","no automatic action")


def advisory_contract(advisory: Advisory) -> dict:
    return {"advisory":asdict(advisory),"policy_required":True,"authorization_required":True,"verification_required":True,"audit_required":True}


# Phase 18 -----------------------------------------------------------------
def storage_economics(observations: Iterable[StorageObservation], *, duplicate_bytes: int = 0) -> dict:
    items=list(observations); total=sum(x.size for x in items); tiers={t:sum(x.size for x in items if x.tier==t) for t in ("hot","warm","cold")}
    return {"total_bytes":total,"file_count":len(items),"hot_bytes":tiers["hot"],"warm_bytes":tiers["warm"],"cold_bytes":tiers["cold"],"duplicate_bytes":max(0,duplicate_bytes),"reclaimable_estimate":max(0,duplicate_bytes),"recommendations": ["review cold data before any transfer"] if tiers["cold"] else []}


def growth_forecast(samples: Iterable[tuple[float,int]]) -> dict:
    values=list(samples)
    if len(values)<2: return {"samples":len(values),"bytes_per_day":0.0,"confidence":"insufficient"}
    xs=[x for x,_ in values]; ys=[y for _,y in values]; mx=statistics.mean(xs); my=statistics.mean(ys); den=sum((x-mx)**2 for x in xs); slope=sum((x-mx)*(y-my) for x,y in values)/den if den else 0.0
    return {"samples":len(values),"bytes_per_day":round(slope*86400,2),"confidence":"observed"}


# Phase 19 -----------------------------------------------------------------
@dataclass(frozen=True)
class SnapshotEntry:
    relative_path: str
    size: int
    sha256: str


def create_snapshot_manifest(root: str | Path, output: str | Path) -> Path:
    base=Path(root).expanduser().resolve(); dest=Path(output); dest.parent.mkdir(parents=True,exist_ok=True)
    entries=[SnapshotEntry(_safe_relative(base,p),p.stat().st_size,_sha256(p)) for p in sorted(base.rglob("*")) if p.is_file()]
    payload={"schema":1,"created_at":_now(),"root":str(base),"entries":[asdict(e) for e in entries]}
    payload["digest"]=hashlib.sha256(json.dumps(payload["entries"],sort_keys=True).encode()).hexdigest()
    dest.write_text(json.dumps(payload,indent=2,sort_keys=True),encoding="utf-8"); return dest


def verify_snapshot_manifest(manifest: str | Path, root: str | Path) -> dict:
    data=json.loads(Path(manifest).read_text(encoding="utf-8")); base=Path(root).expanduser().resolve(); missing=[]; changed=[]
    for item in data.get("entries",[]):
        p=base/item["relative_path"]
        if not p.is_file(): missing.append(item["relative_path"]); continue
        if p.stat().st_size!=item["size"] or _sha256(p)!=item["sha256"]: changed.append(item["relative_path"])
    return {"verified":not missing and not changed,"missing":missing,"changed":changed,"entry_count":len(data.get("entries",[]))}


# Phase 20 -----------------------------------------------------------------
@dataclass(frozen=True)
class IntegrationContract:
    name: str
    version: str
    operations: tuple[str,...]
    production_write: bool = False
    authorization_required: bool = True


def integration_contracts() -> list[IntegrationContract]:
    return [
        IntegrationContract("vajra","1",("catalog.read","plan.read","audit.read")),
        IntegrationContract("engineering-lab","1",("catalog.read","archive.plan","snapshot.read")),
        IntegrationContract("dataset-workflow","1",("catalog.read","integrity.read","export.metadata")),
    ]


# Phase 21 -----------------------------------------------------------------
@dataclass(frozen=True)
class ExperimentSpec:
    name: str
    description: str
    isolation: str = "lab-owned-only"
    production_mutation: bool = False


def experimental_registry() -> list[ExperimentSpec]:
    return [
        ExperimentSpec("content-addressable-index","benchmark content-addressed metadata without moving files"),
        ExperimentSpec("tiering-simulator","simulate tier placement and costs without changing storage"),
        ExperimentSpec("snapshot-compression-benchmark","measure local compression on copied test fixtures"),
        ExperimentSpec("distributed-worker-protocol","protocol-only worker leasing experiment"),
        ExperimentSpec("local-ai-orchestration","advisory-only model orchestration benchmark"),
    ]


# Phase 22 -----------------------------------------------------------------
def control_center_payload(root: str | Path) -> dict:
    """Framework-neutral dashboard payload; a UI can consume this without owning control."""
    observations=observe_storage(root)
    return {"schema":1,"generated_at":_now(),"storage":storage_economics(observations),"cache":cache_pressure(Path(root)/"cache", max(1,shutil.disk_usage(root).total//100)),"integrations":[asdict(x) for x in integration_contracts()],"experiments":[asdict(x) for x in experimental_registry()],"authority":"teldrive","ui_mutation_policy":"none"}


def validate_extended_safety() -> dict:
    return {"production_write":False,"production_delete":False,"automatic_eviction":False,"telldrive_db_write":False,"ai_authority":False,"all_mutations_require_explicit_authorization":True}
