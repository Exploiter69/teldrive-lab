"""Live, read-only Control Center for the TelDrive Lab.

The Control Center is an observer, never an execution authority. It reads only
Lab-owned catalog/job/audit state and exposes deterministic JSON/HTML views.
TelDrive production storage and its database are never written here.
"""
from __future__ import annotations

import html
import json
import os
import platform
import shutil
import sqlite3
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .audit import open_audit
from .catalog import Catalog
from .jobs import JobState, JobStore
from .models import SourceType
from .runtime import ensure_runtime, runtime_paths

MAX_ROWS = 100
MEDIA_EXTENSIONS = {
    ".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v", ".mp3", ".flac",
    ".wav", ".m4a", ".ogg", ".opus", ".aac", ".jpg", ".jpeg", ".png",
    ".webp", ".gif",
}


def _jsonable(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, tuple):
        return list(value)
    return value


def _job(job: Any) -> dict[str, Any]:
    return {k: _jsonable(v) for k, v in asdict(job).items()}


def _record(record: Any) -> dict[str, Any]:
    return {k: _jsonable(v) for k, v in asdict(record).items()}


def _counts(items: list[Any], attr: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for item in items:
        key = str(getattr(item, attr).value if hasattr(getattr(item, attr), "value") else getattr(item, attr))
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))


class ControlCenter:
    """Read-only live state facade over the Lab's durable stores."""

    def __init__(self, state_root: str | Path | None = None) -> None:
        self.paths = ensure_runtime(runtime_paths(state_root) if state_root else None)
        self.catalog = Catalog(self.paths.root / "catalog.db")
        self.jobs = JobStore(self.paths.root / "jobs.db")
        self.audit_path = self.paths.root / "audit.db"

    def catalog_state(self, limit: int = MAX_ROWS) -> dict[str, Any]:
        records = self.catalog.list_source(SourceType.TELDRIVE, "teldrive")
        # Some discovery adapters use a remote-specific source identifier. Count
        # the whole derived catalog and expose a bounded representative sample.
        if not records:
            with self.catalog._connect() as conn:
                rows = conn.execute("SELECT * FROM files ORDER BY last_seen_at DESC, id DESC LIMIT ?", (limit,)).fetchall()
            records = [self.catalog.get(SourceType(row["source_type"]), row["source_identifier"], row["path"]) for row in rows]
            records = [r for r in records if r is not None]
        records = records[:limit]
        return {
            "total": self.catalog.count(),
            "sample": [_record(r) for r in records],
            "source_counts": self._catalog_source_counts(),
            "verification_counts": self._catalog_verification_counts(),
        }

    def _catalog_source_counts(self) -> dict[str, int]:
        with self.catalog._connect() as conn:
            rows = conn.execute("SELECT source_type, COUNT(*) AS n FROM files GROUP BY source_type ORDER BY source_type").fetchall()
        return {str(r["source_type"]): int(r["n"]) for r in rows}

    def _catalog_verification_counts(self) -> dict[str, int]:
        with self.catalog._connect() as conn:
            rows = conn.execute("SELECT verification_state, COUNT(*) AS n FROM files GROUP BY verification_state ORDER BY verification_state").fetchall()
        return {str(r["verification_state"]): int(r["n"]) for r in rows}

    def jobs_state(self, limit: int = MAX_ROWS) -> dict[str, Any]:
        jobs = self.jobs.list_jobs(limit=limit)
        counts = {state.value: len(self.jobs.list_jobs(state=state, limit=1000)) for state in JobState}
        return {"total_known": sum(counts.values()), "counts": counts, "items": [_job(j) for j in jobs]}

    def transfers_state(self, limit: int = MAX_ROWS) -> dict[str, Any]:
        transfer_types = {"UPLOAD", "DOWNLOAD", "ARCHIVE", "BACKUP", "SNAPSHOT", "RESTORE", "CLEANUP", "ORGANIZE"}
        jobs = [j for j in self.jobs.list_jobs(limit=1000) if j.type.value in transfer_types]
        return {"total": len(jobs), "active": sum(j.state in {JobState.RUNNING, JobState.VERIFYING} for j in jobs), "items": [_job(j) for j in jobs[:limit]]}

    def media_state(self, limit: int = MAX_ROWS) -> dict[str, Any]:
        with self.catalog._connect() as conn:
            rows = conn.execute("SELECT * FROM files WHERE LOWER(extension) IN ({}) ORDER BY last_seen_at DESC, id DESC LIMIT ?".format(",".join("?" for _ in MEDIA_EXTENSIONS)), tuple(sorted(MEDIA_EXTENSIONS)) + (limit,)).fetchall()
        items = [self.catalog.get(SourceType(r["source_type"]), r["source_identifier"], r["path"]) for r in rows]
        items = [r for r in items if r is not None]
        return {"total": len(items), "items": [_record(r) for r in items]}

    def search_state(self, query: str, limit: int = 50) -> dict[str, Any]:
        if not query.strip():
            return {"query": query, "count": 0, "items": []}
        results = self.catalog.search(query, limit=min(max(1, limit), 500))
        return {"query": query, "count": len(results), "items": [_record(r) for r in results]}

    def health_state(self) -> dict[str, Any]:
        usage = shutil.disk_usage(self.paths.root)
        state = {
            "ok": True,
            "authority": "teldrive",
            "mutation": "none",
            "lab_state": str(self.paths.root),
            "disk": {"total": usage.total, "used": usage.used, "free": usage.free},
            "platform": platform.platform(),
            "python": platform.python_version(),
            "pid": os.getpid(),
            "uptime_seconds": self._uptime_seconds(),
        }
        # Opening the three stores is itself a useful readiness check.
        try:
            self.catalog.count()
            self.jobs.list_jobs(limit=1)
            with open_audit(self.audit_path) as conn:
                conn.execute("SELECT 1").fetchone()
        except Exception as exc:  # pragma: no cover - defensive health boundary
            state["ok"] = False
            state["error"] = type(exc).__name__
        return state

    @staticmethod
    def _uptime_seconds() -> float | None:
        try:
            return time.time() - float(Path("/proc/uptime").read_text().split()[0])
        except (OSError, ValueError, IndexError):
            return None

    def audit_state(self, limit: int = MAX_ROWS) -> dict[str, Any]:
        if not self.audit_path.exists():
            return {"total": 0, "items": []}
        with open_audit(self.audit_path) as conn:
            rows = conn.execute("SELECT id,event_id,timestamp,operation,job_id,source,destination,decision,result,checksum,error_code,details_json FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            total = int(conn.execute("SELECT COUNT(*) FROM events").fetchone()[0])
        items = []
        for row in rows:
            item = dict(row)
            try:
                item["details"] = json.loads(item.pop("details_json"))
            except (TypeError, json.JSONDecodeError):
                item["details"] = {}
            items.append(item)
        return {"total": total, "items": items}

    def config_state(self) -> dict[str, Any]:
        return {
            "mode": "READ_ONLY_OBSERVER",
            "authority": "teldrive",
            "ui_mutation_policy": "none",
            "state_root": str(self.paths.root),
            "catalog": str(self.catalog.path),
            "jobs": str(self.jobs.path),
            "audit": str(self.audit_path),
            "paid_dependencies": False,
            "direct_teldrive_db_writes": False,
            "production_mutation": False,
        }

    def dashboard(self) -> dict[str, Any]:
        health = self.health_state()
        catalog = self.catalog_state(limit=20)
        jobs = self.jobs_state(limit=20)
        transfers = self.transfers_state(limit=20)
        media = self.media_state(limit=20)
        audit = self.audit_state(limit=20)
        return {
            "schema": "teldrive-lab.control-center.v1",
            "generated_at": time.time(),
            "authority": "teldrive",
            "ui_mutation_policy": "none",
            "health": health,
            "catalog": catalog,
            "jobs": jobs,
            "transfers": transfers,
            "media": media,
            "audit": audit,
            "routes": ["/api/dashboard", "/api/catalog", "/api/jobs", "/api/transfers", "/api/media", "/api/search?q=", "/api/health", "/api/audit", "/api/config"],
        }


def _page() -> bytes:
    body = """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>TelDrive Lab Control Center</title><style>body{font-family:system-ui,sans-serif;background:#111;color:#eee;margin:0;padding:24px}h1{font-size:22px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.card{border:1px solid #444;padding:16px;border-radius:8px}.muted{color:#aaa}pre{white-space:pre-wrap;max-height:60vh;overflow:auto}</style></head><body><h1>TelDrive Lab — Live Control Center</h1><p class='muted'>Read-only observer. TelDrive remains storage authority. No UI mutation.</p><div id='cards' class='grid'></div><h2>Live state</h2><pre id='out'>Loading…</pre><script>async function load(){const r=await fetch('/api/dashboard');const x=await r.json();document.getElementById('cards').innerHTML=`<div class='card'>Catalog<br><b>${x.catalog.total}</b></div><div class='card'>Jobs<br><b>${x.jobs.total_known}</b></div><div class='card'>Transfers<br><b>${x.transfers.total}</b></div><div class='card'>Media<br><b>${x.media.total}</b></div><div class='card'>Audit events<br><b>${x.audit.total}</b></div><div class='card'>Health<br><b>${x.health.ok?'OK':'DEGRADED'}</b></div>`;document.getElementById('out').textContent=JSON.stringify(x,null,2)}load().catch(e=>document.getElementById('out').textContent=String(e))</script></body></html>"""
    return body.encode()


def control_center_server(state_root: str | Path | None = None, host: str = "127.0.0.1", port: int = 8790):
    from .advanced import validate_loopback_host
    validate_loopback_host(host)
    provider = ControlCenter(state_root)

    class Handler(__import__("http.server").server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            try:
                if parsed.path == "/":
                    body = _page()
                elif parsed.path == "/api/dashboard":
                    body = json.dumps(provider.dashboard(), default=str).encode()
                elif parsed.path == "/api/catalog":
                    body = json.dumps(provider.catalog_state(), default=str).encode()
                elif parsed.path == "/api/jobs":
                    body = json.dumps(provider.jobs_state(), default=str).encode()
                elif parsed.path == "/api/transfers":
                    body = json.dumps(provider.transfers_state(), default=str).encode()
                elif parsed.path == "/api/media":
                    body = json.dumps(provider.media_state(), default=str).encode()
                elif parsed.path == "/api/search":
                    query = parse_qs(parsed.query).get("q", [""])[0]
                    body = json.dumps(provider.search_state(query), default=str).encode()
                elif parsed.path == "/api/health":
                    body = json.dumps(provider.health_state(), default=str).encode()
                elif parsed.path == "/api/audit":
                    body = json.dumps(provider.audit_state(), default=str).encode()
                elif parsed.path == "/api/config":
                    body = json.dumps(provider.config_state(), default=str).encode()
                else:
                    self.send_response(404); self.end_headers(); return
            except Exception as exc:
                body = json.dumps({"ok": False, "error": type(exc).__name__, "message": str(exc)}).encode()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers(); self.wfile.write(body); return
            self.send_response(200); self.send_header("Content-Type", "application/json" if parsed.path != "/" else "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

        def do_POST(self) -> None: self.send_response(405); self.send_header("Allow", "GET"); self.end_headers()
        def do_PUT(self) -> None: self.send_response(405); self.send_header("Allow", "GET"); self.end_headers()
        def do_PATCH(self) -> None: self.send_response(405); self.send_header("Allow", "GET"); self.end_headers()
        def do_DELETE(self) -> None: self.send_response(405); self.send_header("Allow", "GET"); self.end_headers()
        def log_message(self, *args: Any) -> None: pass

    import http.server
    return http.server.ThreadingHTTPServer((host, port), Handler)
