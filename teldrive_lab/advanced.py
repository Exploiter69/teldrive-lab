"""Canonical zero-cost Phase 12-22 capability layer.

This module is the single canonical implementation for advanced Lab capabilities.
It is Lab-owned and advisory/read-only by default; TelDrive remains the production
storage authority. Filesystem scans and content reads are bounded and streaming.

The Lab deliberately does not embed speech-to-text or local-LLM providers.
"""
from __future__ import annotations

import gzip
import hashlib
import http.client
import http.server
import ipaddress
import json
import math
import mimetypes
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

from .resources import (
    DEFAULT_MAX_DEPTH,
    DEFAULT_MAX_FILES,
    DEFAULT_SAMPLE_BYTES,
    ResourceLimitError,
    bounded_sample,
    copy_stream,
    iter_files,
    read_text_bounded,
    stream_sha256,
)


def _files(root: Path, *, max_depth: int = DEFAULT_MAX_DEPTH, max_files: int = DEFAULT_MAX_FILES) -> list[Path]:
    return list(iter_files(root, max_depth=max_depth, max_files=max_files))


@dataclass(frozen=True)
class AccessSample:
    path: str
    accessed_at: float
    bytes_read: int = 0


@dataclass(frozen=True)
class StorageHeat:
    path: str
    size: int
    accesses: int
    last_access: float
    tier: str
    score: float


def storage_tier(accesses: int, age_seconds: float, *, hot_accesses: int = 8, warm_age: float = 30 * 86400) -> str:
    if accesses >= hot_accesses or age_seconds <= 7 * 86400:
        return "hot"
    if accesses > 0 or age_seconds <= warm_age:
        return "warm"
    return "cold"


def record_access(db: Path, path: str, *, bytes_read: int = 0, when: float | None = None) -> None:
    db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db) as c:
        c.execute("CREATE TABLE IF NOT EXISTS access(path TEXT, accessed_at REAL, bytes_read INTEGER)")
        c.execute("INSERT INTO access VALUES(?,?,?)", (str(Path(path).resolve()), when or time.time(), bytes_read))


def access_frequency(db: Path, paths: Iterable[str] | None = None, now: float | None = None) -> dict[str, int]:
    if not db.exists():
        return {}
    allowed = {str(Path(p).resolve()) for p in paths} if paths else None
    with sqlite3.connect(db) as c:
        rows = c.execute("SELECT path,COUNT(*) FROM access GROUP BY path").fetchall()
    return {p: int(n) for p, n in rows if allowed is None or p in allowed}


def storage_heatmap(root: Path, access_db: Path | None = None, *, now: float | None = None, max_depth: int = DEFAULT_MAX_DEPTH, max_files: int = DEFAULT_MAX_FILES) -> list[StorageHeat]:
    current = now or time.time()
    freq = access_frequency(access_db) if access_db else {}
    result = []
    for p in _files(root, max_depth=max_depth, max_files=max_files):
        try:
            stat = p.stat()
        except OSError:
            continue
        n = freq.get(str(p.resolve()), 0)
        age = max(0, current - stat.st_mtime)
        tier = storage_tier(n, age)
        score = n / (1 + age / 86400)
        result.append(StorageHeat(str(p), stat.st_size, n, stat.st_mtime, tier, round(score, 6)))
    return result


def prefetch_suggestions(heat: Iterable[StorageHeat], *, limit: int = 20) -> list[dict[str, Any]]:
    return [
        {"path": x.path, "reason": "high_recent_access", "score": x.score, "action": "PREFETCH_SUGGESTION"}
        for x in sorted((h for h in heat if h.tier == "hot"), key=lambda h: (-h.score, h.path))[:limit]
    ]


def cache_pressure(root: Path, capacity_bytes: int, *, max_depth: int = DEFAULT_MAX_DEPTH, max_files: int = DEFAULT_MAX_FILES) -> dict[str, Any]:
    used = sum(p.stat().st_size for p in _files(root, max_depth=max_depth, max_files=max_files))
    ratio = used / capacity_bytes if capacity_bytes else 1.0
    return {"used_bytes": used, "capacity_bytes": capacity_bytes, "ratio": ratio, "pressure": "critical" if ratio >= .95 else "high" if ratio >= .8 else "normal"}


def eviction_plan(heat: Iterable[StorageHeat], target_free_bytes: int) -> dict[str, Any]:
    candidates = sorted((h for h in heat if h.tier == "cold"), key=lambda h: (h.score, -h.size, h.path))
    selected = []
    total = 0
    for h in candidates:
        if total >= target_free_bytes:
            break
        selected.append({"path": h.path, "size": h.size, "tier": h.tier, "action": "PLAN_ONLY"})
        total += h.size
    return {"action": "PLAN_ONLY", "target_free_bytes": target_free_bytes, "planned_bytes": total, "items": selected}


def resource_budget(ram_available_mb: int, per_worker_mb: int, cpu_count: int | None = None, max_workers: int = 8) -> int:
    return max(1, min(max_workers, max(1, ram_available_mb // max(1, per_worker_mb)), cpu_count or (os.cpu_count() or 1)))


def export_metadata(records: Iterable[dict[str, Any]], destination: Path) -> dict[str, Any]:
    payload = {"schema": "teldrive-lab.metadata.v1", "generated_at": time.time(), "records": list(records)}
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return {"path": str(destination), "records": len(payload["records"]), "schema": payload["schema"]}


def validate_metadata_export(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    ok = data.get("schema") == "teldrive-lab.metadata.v1" and isinstance(data.get("records"), list)
    return {"valid": ok, "schema": data.get("schema"), "records": len(data.get("records", []))}


def import_metadata(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    result = validate_metadata_export(path)
    if not result["valid"]:
        raise ValueError("invalid metadata export")
    return list(data["records"])


def filesystem_metadata_view(root: Path, *, max_depth: int = DEFAULT_MAX_DEPTH, max_files: int = DEFAULT_MAX_FILES) -> list[dict[str, Any]]:
    out = []
    base = root.expanduser().resolve()
    if base.exists():
        try:
            s = base.stat()
            out.append({"path": str(base), "name": base.name, "size": s.st_size if base.is_file() else None, "mtime": s.st_mtime, "is_dir": base.is_dir()})
        except OSError:
            pass
    for p in _files(base, max_depth=max_depth, max_files=max_files):
        try:
            s = p.stat()
            out.append({"path": str(p), "name": p.name, "size": s.st_size, "mtime": s.st_mtime, "is_dir": False})
        except OSError:
            continue
    return out


def validate_loopback_host(host: str) -> str:
    value = host.strip().lower().strip("[]")
    if value == "localhost":
        addresses = {item[4][0] for item in socket.getaddrinfo("localhost", None, type=socket.SOCK_STREAM)}
        if addresses and not all(ipaddress.ip_address(addr).is_loopback for addr in addresses):
            raise ValueError("localhost does not resolve exclusively to loopback")
        return host
    try:
        address = ipaddress.ip_address(value)
    except ValueError as exc:
        raise ValueError("HTTP API must bind to loopback (127.0.0.1 or ::1)") from exc
    if not address.is_loopback:
        raise ValueError("HTTP API refuses non-loopback binding")
    return host


class ReadOnlyJSONAPI:
    def __init__(self, provider):
        self.provider = provider

    def handler(self):
        provider = self.provider

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/health":
                    data = {"ok": True, "authority": "teldrive", "mutation": "none"}
                elif self.path == "/metadata":
                    data = provider()
                else:
                    self.send_response(404)
                    self.end_headers()
                    return
                body = json.dumps(data, default=str).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                self.send_response(405)
                self.end_headers()

            def do_PUT(self):
                self.send_response(405)
                self.end_headers()

            def do_DELETE(self):
                self.send_response(405)
                self.end_headers()

            def log_message(self, *a):
                pass

        return Handler


def serve_json_api(provider, host="127.0.0.1", port=8787) -> http.server.ThreadingHTTPServer:
    validate_loopback_host(host)
    return http.server.ThreadingHTTPServer((host, port), ReadOnlyJSONAPI(provider).handler())


def ipc_request(socket_path: Path, request: dict[str, Any]) -> dict[str, Any]:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(str(socket_path))
        s.sendall((json.dumps(request) + "\n").encode())
        return json.loads(s.recv(1_048_576).decode())


MEDIA_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".mp3", ".flac", ".wav", ".m4a", ".ogg", ".opus", ".jpg", ".jpeg", ".png", ".webp", ".gif"}
SUBTITLE_EXTENSIONS = {".srt", ".vtt", ".ass", ".ssa"}


def media_records(root: Path, *, max_depth: int = DEFAULT_MAX_DEPTH, max_files: int = DEFAULT_MAX_FILES) -> list[dict[str, Any]]:
    out = []
    for p in _files(root, max_depth=max_depth, max_files=max_files):
        if p.suffix.lower() not in MEDIA_EXTENSIONS:
            continue
        try:
            s = p.stat()
        except OSError:
            continue
        out.append({"path": str(p), "name": p.name, "extension": p.suffix.lower(), "mime": mimetypes.guess_type(p.name)[0], "size": s.st_size, "mtime": s.st_mtime})
    return out


def subtitle_index(root: Path, *, max_depth: int = DEFAULT_MAX_DEPTH, max_files: int = DEFAULT_MAX_FILES) -> list[dict[str, Any]]:
    return [{"path": str(p), "stem": p.stem, "language_hint": p.suffix.lower(), "size": p.stat().st_size} for p in _files(root, max_depth=max_depth, max_files=max_files) if p.suffix.lower() in SUBTITLE_EXTENSIONS]


def _optional_command(command: list[str], *, timeout: int = 30) -> tuple[bool, str]:
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        return proc.returncode == 0, proc.stdout
    except (FileNotFoundError, subprocess.SubprocessError):
        return False, ""


def media_probe(path: Path) -> dict[str, Any]:
    ok, out = _optional_command(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(path)])
    if ok:
        try:
            return {"available": True, "data": json.loads(out)}
        except json.JSONDecodeError:
            pass
    return {"available": False, "data": {"name": path.name, "size": path.stat().st_size}}


def thumbnail_capability() -> dict[str, Any]:
    return {"ffmpeg": shutil.which("ffmpeg") is not None, "ffprobe": shutil.which("ffprobe") is not None, "policy": "sidecar_only"}


@dataclass(frozen=True)
class MediaIntegration:
    name: str
    endpoint: str
    mode: str = "READ_ONLY"


def media_integrations() -> list[MediaIntegration]:
    return [MediaIntegration("jellyfin", "/Items", "READ_ONLY"), MediaIntegration("plex", "/library/metadata", "READ_ONLY")]


def remote_metadata_request(base_url: str, path: str, *, token: str | None = None, timeout: int = 10) -> dict[str, Any]:
    u = urlparse(base_url)
    conn = http.client.HTTPSConnection(u.hostname, u.port or 443, timeout=timeout) if u.scheme == "https" else http.client.HTTPConnection(u.hostname, u.port or 80, timeout=timeout)
    headers = {"Accept": "application/json"}
    if token:
        headers["X-Emby-Token"] = token
    conn.request("GET", path, headers=headers)
    response = conn.getresponse()
    raw = response.read()
    if response.status >= 400:
        raise RuntimeError(f"integration HTTP {response.status}")
    return json.loads(raw.decode("utf-8"))


def text_extract(path: Path, max_bytes: int = DEFAULT_SAMPLE_BYTES) -> str:
    if max_bytes < 0:
        raise ValueError("max_bytes must be non-negative")
    if path.suffix.lower() in {".txt", ".md", ".rst", ".csv", ".json", ".yaml", ".yml", ".log", ".srt", ".vtt"}:
        return read_text_bounded(path, max_bytes)
    ok, out = _optional_command(["pdftotext", "-layout", str(path), "-"], timeout=30) if path.suffix.lower() == ".pdf" else (False, "")
    return out[:max_bytes] if ok else ""


def pdf_metadata(path: Path) -> dict[str, Any]:
    ok, out = _optional_command(["pdfinfo", str(path)], timeout=20) if path.suffix.lower() == ".pdf" else (False, "")
    fields = {}
    if ok:
        for line in out.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                fields[k.strip()] = v.strip()
    return {"available": ok, "fields": fields}


def document_fingerprint(path: Path) -> dict[str, Any]:
    digest, size = stream_sha256(path)
    text = text_extract(path)
    return {"sha256": digest, "size": size, "text_available": bool(text), "text_chars": len(text), "pdf": pdf_metadata(path) if path.suffix.lower() == ".pdf" else None}


def ocr(path: Path, *, language="eng", timeout=60) -> dict[str, Any]:
    ok, out = _optional_command(["tesseract", str(path), "stdout", "-l", language], timeout=timeout)
    return {"available": ok, "text": out if ok else "", "tool": "tesseract"}


def local_embedding(text: str, dimensions: int = 256) -> list[float]:
    vec = [0.0] * dimensions
    for token in re.findall(r"\w+", text.lower()):
        digest = hashlib.sha256(token.encode()).digest()
        idx = int.from_bytes(digest[:4], "big") % dimensions
        vec[idx] += 1 if digest[4] & 1 else -1
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def image_vision_summary(path: Path, *, max_bytes: int = DEFAULT_SAMPLE_BYTES) -> dict[str, Any]:
    data = bounded_sample(path, max_bytes)
    return {"path": str(path), "bytes_sampled": len(data), "sha256_sample": hashlib.sha256(data).hexdigest(), "vision_model": "none", "advisory": True}


def tokenize(text: str) -> list[str]:
    return re.findall(r"[\w.-]+", text.lower())


def content_index(paths: Iterable[Path], *, max_bytes: int = DEFAULT_SAMPLE_BYTES) -> dict[str, Any]:
    docs = {}
    df = {}
    for p in paths:
        text = text_extract(p, max_bytes=max_bytes)
        if not text:
            continue
        tokens = tokenize(text)
        counts = {t: tokens.count(t) for t in set(tokens)}
        docs[str(p)] = {"text": text, "counts": counts, "embedding": local_embedding(text)}
        for token in counts:
            df[token] = df.get(token, 0) + 1
    return {"docs": docs, "df": df, "count": len(docs)}


def search_content(index: dict[str, Any], query: str, limit: int = 20) -> list[dict[str, Any]]:
    q = tokenize(query)
    docs = index.get("docs", {})
    n_docs = max(1, len(docs))
    scored = []
    qv = local_embedding(query)
    for path, doc in docs.items():
        score = 0.0
        for token in q:
            tf = doc["counts"].get(token, 0)
            df = index.get("df", {}).get(token, 0)
            if tf:
                score += (1 + math.log(tf)) * math.log((n_docs + 1) / (df + 1))
        score += 0.1 * sum(a * b for a, b in zip(qv, doc["embedding"]))
        if score > 0:
            scored.append({"path": path, "score": round(score, 6), "matches": sum(doc["counts"].get(t, 0) for t in q)})
    return sorted(scored, key=lambda x: (-x["score"], x["path"]))[:limit]


@dataclass(frozen=True)
class AIProposal:
    action: str
    rationale: str
    confidence: float
    authoritative: bool = False
    requires_policy: bool = True
    requires_authorization: bool = True


def ai_proposal(action: str, rationale: str, confidence: float = 0.5) -> AIProposal:
    return AIProposal(action, rationale, max(0, min(1, confidence)))


def natural_language_search(query: str, index: dict[str, Any]) -> list[dict[str, Any]]:
    return search_content(index, query)


def organization_suggestions(records: Iterable[dict[str, Any]]) -> list[AIProposal]:
    out = []
    for record in records:
        ext = str(record.get("extension", "")).lower()
        target = "media" if ext in MEDIA_EXTENSIONS else "documents" if ext in {".pdf", ".md", ".txt", ".docx"} else "review"
        out.append(ai_proposal("CLASSIFY", f"Suggested category {target} for {record.get('name', record.get('path', 'item'))}", .55))
    return out


def anomaly_explanations(metrics: dict[str, Any]) -> list[AIProposal]:
    out = []
    if metrics.get("growth_rate", 0) > metrics.get("growth_threshold", 1):
        out.append(ai_proposal("REVIEW_GROWTH", "Observed growth exceeds configured threshold", .8))
    if metrics.get("integrity_failures", 0):
        out.append(ai_proposal("REVIEW_INTEGRITY", "Integrity failures require verification", .95))
    return out


def category_analysis(paths: Iterable[Path]) -> dict[str, dict[str, int]]:
    out = {}
    for p in paths:
        try:
            size = p.stat().st_size
        except OSError:
            continue
        category = p.suffix.lower() or "[no_extension]"
        row = out.setdefault(category, {"files": 0, "bytes": 0})
        row["files"] += 1
        row["bytes"] += size
    return dict(sorted(out.items()))


def growth_forecast(samples: Iterable[tuple[float, int]], horizon_days: int = 30) -> dict[str, Any]:
    pts = list(samples)
    if len(pts) < 2:
        return {"bytes_per_day": 0.0, "forecast_bytes": pts[-1][1] if pts else 0, "confidence": "insufficient"}
    x0, y0 = pts[0]
    x1, y1 = pts[-1]
    rate = (y1 - y0) / max(1, x1 - x0) * 86400
    return {"bytes_per_day": rate, "forecast_bytes": max(0, int(y1 + rate * horizon_days)), "horizon_days": horizon_days, "confidence": "trend"}


def storage_economics(heat: Iterable[StorageHeat], duplicate_bytes: int = 0) -> dict[str, Any]:
    items = list(heat)
    total = sum(x.size for x in items)
    hot = sum(x.size for x in items if x.tier == "hot")
    cold = sum(x.size for x in items if x.tier == "cold")
    return {"total_bytes": total, "hot_bytes": hot, "cold_bytes": cold, "duplicate_bytes": duplicate_bytes, "reclaimable_estimate": max(0, duplicate_bytes), "currency": "NONE", "paid_service": False}


def transfer_cost_estimate(bytes_count: int, *, seconds_per_gb: float = 60, bandwidth_mbps: float = 100) -> dict[str, Any]:
    seconds = bytes_count * 8 / (max(.001, bandwidth_mbps) * 1_000_000)
    return {"bytes": bytes_count, "estimated_seconds": seconds, "estimated_minutes": seconds / 60, "bandwidth_mbps": bandwidth_mbps, "currency": "NONE", "advisory": True}


def manifest_tree(root: Path, *, max_depth: int = DEFAULT_MAX_DEPTH, max_files: int = DEFAULT_MAX_FILES) -> dict[str, dict[str, Any]]:
    base = root.expanduser().resolve()
    out = {}
    for p in _files(base, max_depth=max_depth, max_files=max_files):
        digest, size = stream_sha256(p)
        out[str(p.relative_to(base))] = {"size": size, "sha256": digest, "mtime": p.stat().st_mtime}
    return out


def create_snapshot(root: Path, destination: Path, parent: dict[str, Any] | None = None, *, max_depth: int = DEFAULT_MAX_DEPTH, max_files: int = DEFAULT_MAX_FILES) -> dict[str, Any]:
    files = manifest_tree(root, max_depth=max_depth, max_files=max_files)
    parent_files = (parent or {}).get("files", {})
    changed = {k: v for k, v in files.items() if parent_files.get(k) != v}
    deleted = sorted(set(parent_files) - set(files))
    body = {"schema": "teldrive-lab.snapshot.v2", "created_at": time.time(), "root": str(root), "parent_digest": (parent or {}).get("digest"), "files": files, "incremental": {"changed": changed, "deleted": deleted}}
    body["digest"] = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(body, indent=2, sort_keys=True), encoding="utf-8")
    return body


def verify_snapshot(path: Path, root: Path, *, max_depth: int = DEFAULT_MAX_DEPTH, max_files: int = DEFAULT_MAX_FILES) -> dict[str, Any]:
    data = json.loads(path.read_text())
    expected = data.get("files", {})
    actual = manifest_tree(root, max_depth=max_depth, max_files=max_files)
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    changed = sorted(k for k in set(expected) & set(actual) if expected[k]["sha256"] != actual[k]["sha256"] or expected[k]["size"] != actual[k]["size"])
    return {"verified": not missing and not extra and not changed, "missing": missing, "extra": extra, "changed": changed}


def retention_plan(snapshots: Iterable[dict[str, Any]], keep: int) -> dict[str, Any]:
    ordered = sorted(snapshots, key=lambda x: x.get("created_at", 0), reverse=True)
    return {"keep": ordered[:keep], "expire": ordered[keep:], "action": "PLAN_ONLY"}


def restore_plan(snapshot: dict[str, Any], destination: Path) -> dict[str, Any]:
    items = []
    for rel, meta in sorted(snapshot.get("files", {}).items()):
        target = destination / rel
        items.append({"source": rel, "destination": str(target), "sha256": meta["sha256"], "action": "CREATE" if not target.exists() else "VERIFY_EXISTING"})
    return {"snapshot_digest": snapshot.get("digest"), "destination": str(destination), "items": items, "action": "PLAN_ONLY", "requires_authorization": True}


@dataclass(frozen=True)
class ProjectContract:
    name: str
    version: str
    capabilities: tuple[str, ...]
    production_write: bool = False
    authorization: str = "caller_owned"


def project_contracts() -> list[ProjectContract]:
    return [ProjectContract("VAJRA", "1", ("artifact_export", "snapshot_manifest", "read_metadata", "archive_plan")), ProjectContract("Alok Engineering Lab", "1", ("artifact_export", "read_metadata", "experiment_archive")), ProjectContract("local-development", "1", ("read_metadata", "dataset_export", "snapshot_manifest")), ProjectContract("dataset-workflow", "1", ("read_metadata", "content_search", "integrity_report")), ProjectContract("experiment-archive", "1", ("artifact_export", "snapshot_manifest", "integrity_report"))]


def validate_project_request(contract: ProjectContract, capability: str, *, production_write: bool = False) -> dict[str, Any]:
    allowed = capability in contract.capabilities and not production_write and not contract.production_write
    return {"allowed": allowed, "contract": contract.name, "capability": capability, "production_write": production_write, "reason": "OK" if allowed else "BLOCKED"}


class CASStore:
    def __init__(self, root: Path):
        self.root = root

    def put(self, source: Path) -> str:
        digest, size = stream_sha256(source)
        dest = self.root / digest[:2] / digest[2:4] / digest
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            return digest
        temp = dest.with_name(dest.name + f".partial-{os.getpid()}-{threading.get_ident()}")
        try:
            copied_digest, copied_size = copy_stream(source, temp)
            if copied_digest != digest or copied_size != size:
                raise IOError("CAS source changed during copy")
            os.replace(temp, dest)
        finally:
            try:
                temp.unlink()
            except FileNotFoundError:
                pass
        return digest

    def has(self, digest: str) -> bool:
        return (self.root / digest[:2] / digest[2:4] / digest).is_file()


def dedup_plan(paths: Iterable[Path]) -> list[dict[str, Any]]:
    groups = {}
    for p in paths:
        if not p.is_file():
            continue
        digest, size = stream_sha256(p)
        groups.setdefault((digest, size), []).append(str(p))
    return [{"sha256": digest, "size": size, "copies": sorted(ps), "reclaimable_bytes": size * (len(ps) - 1), "action": "REPORT_ONLY"} for (digest, size), ps in sorted(groups.items()) if len(ps) > 1]


def tiering_plan(heat: Iterable[StorageHeat]) -> list[dict[str, Any]]:
    return [{"path": h.path, "from": h.tier, "suggested": "cold" if h.tier == "warm" else "warm" if h.tier == "hot" else "cold", "action": "PLAN_ONLY"} for h in heat]


def compressed_snapshot(snapshot_path: Path, destination: Path, *, max_bytes: int = 100 * 1024 * 1024) -> dict[str, Any]:
    source_digest, source_size = stream_sha256(snapshot_path)
    if source_size > max_bytes:
        raise ResourceLimitError(f"snapshot exceeds max_bytes={max_bytes}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with snapshot_path.open("rb") as src, gzip.open(destination, "wb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)
    digest = hashlib.sha256()
    size = 0
    with gzip.open(destination, "rb") as src:
        while True:
            chunk = src.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    return {"source": str(snapshot_path), "destination": str(destination), "bytes_before": source_size, "bytes_after": destination.stat().st_size, "verified": size == source_size and digest.hexdigest() == source_digest}


@dataclass(frozen=True)
class WorkerNode:
    node_id: str
    endpoint: str
    capabilities: tuple[str, ...]
    trusted: bool = False


def worker_registry(nodes: Iterable[WorkerNode]) -> dict[str, Any]:
    return {"nodes": [asdict(n) for n in nodes], "dispatch_policy": "explicitly_trusted_only", "production_mutation": False}


def dispatch_plan(node: WorkerNode, job: dict[str, Any]) -> dict[str, Any]:
    return {"node": node.node_id, "job": job, "allowed": node.trusted and not job.get("production_mutation", False), "action": "PLAN_ONLY"}


def ai_workflow_plan(steps: Iterable[dict[str, Any]]) -> dict[str, Any]:
    return {"steps": [{"id": s.get("id", f"step-{i + 1}"), "kind": s.get("kind", "advisory"), "requires_policy": True, "requires_authorization": True, "requires_verification": True, "index": i} for i, s in enumerate(steps)], "authority": "policy", "ai_authoritative": False}


CONTROL_HTML = """<!doctype html><html><head><meta charset='utf-8'><title>TelDrive Lab Control Center</title><style>body{font:15px system-ui;max-width:1100px;margin:40px auto;padding:0 20px}pre{background:#f4f4f4;padding:16px;overflow:auto}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}.card{border:1px solid #ddd;padding:16px}</style></head><body><h1>TelDrive Lab</h1><p>Read-only local control center. TelDrive remains storage authority.</p><div class='grid'><div class='card'>Health<br><code>/api/health</code></div><div class='card'>Metadata<br><code>/api/metadata</code></div><div class='card'>Audit<br><code>/api/audit</code></div><div class='card'>Storage<br><code>/api/storage</code></div></div><pre id='out'>Loading…</pre><script>fetch('/api/health').then(r=>r.json()).then(x=>document.getElementById('out').textContent=JSON.stringify(x,null,2))</script></body></html>"""


def control_center_payload(*, health: dict[str, Any] | None = None, storage: Any = None, jobs: Any = None, audit: Any = None) -> dict[str, Any]:
    return {"authority": "teldrive", "ui_mutation_policy": "none", "routes": ["/", "/api/health", "/api/metadata", "/api/storage", "/api/jobs", "/api/audit"], "health": health or {}, "storage": storage or {}, "jobs": jobs or {}, "audit": audit or {}}


class ControlCenterHandler(http.server.BaseHTTPRequestHandler):
    provider = lambda self: control_center_payload()

    def do_GET(self):
        if self.path == "/":
            body = CONTROL_HTML.encode()
            ctype = "text/html"
        elif self.path.startswith("/api/"):
            body = json.dumps(self.provider(), default=str).encode()
            ctype = "application/json"
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        self.send_response(405)
        self.end_headers()

    def do_PUT(self):
        self.send_response(405)
        self.end_headers()

    def do_DELETE(self):
        self.send_response(405)
        self.end_headers()

    def log_message(self, *args):
        pass


def control_center_server(provider=lambda: control_center_payload(), host="127.0.0.1", port=8790):
    validate_loopback_host(host)

    class Handler(ControlCenterHandler):
        pass

    Handler.provider = lambda self: provider()
    return http.server.ThreadingHTTPServer((host, port), Handler)


def extended_safety() -> dict[str, bool]:
    return {"production_write": False, "production_delete": False, "automatic_eviction": False, "teldrive_db_write": False, "ai_authority": False, "ui_mutation": False, "remote_worker_mutation": False, "all_mutations_require_explicit_authorization": True}


__all__ = [name for name in globals() if not name.startswith("_")]
