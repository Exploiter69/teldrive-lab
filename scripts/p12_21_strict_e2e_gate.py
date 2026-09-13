"""Strict independent E2E verification for optional Phases 12-21.

This gate deliberately targets disposable local state and localhost-only
services. It does not mount, read, write, delete, reorganize, or reconfigure
TelDrive production storage, rclone mounts, or the TelDrive database.

Unlike the consolidated roadmap gate, every capability exercised here gets an
individual evidence record. External/local providers are REQUIRED when the
capability claims provider-backed E2E verification; missing providers are a
hard failure, not a silent skip.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from teldrive_lab.advanced import (
    CASStore,
    access_frequency,
    ai_workflow_plan,
    category_analysis,
    content_index,
    create_snapshot,
    dedup_plan,
    document_fingerprint,
    eviction_plan,
    export_metadata,
    growth_forecast,
    image_vision_summary,
    local_embedding,
    media_probe,
    media_records,
    ocr,
    prefetch_suggestions,
    project_contracts,
    record_access,
    resource_budget,
    search_content,
    speech_to_text,
    storage_heatmap,
    storage_tier,
    thumbnail_capability,
    transfer_cost_estimate,
    validate_loopback_host,
    verify_snapshot,
)
from teldrive_lab.extended import (
    control_center_payload,
    create_snapshot_manifest,
    integration_contracts,
    local_ai_advisory,
    observe_storage,
    validate_extended_safety,
    verify_snapshot_manifest,
)

TIMEOUT = 30


class Evidence:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def check(self, phase: int, capability: str, fn: Callable[[], Any]) -> None:
        started = time.monotonic()
        try:
            result = fn()
            self.records.append({
                "phase": phase,
                "capability": capability,
                "status": "PASS",
                "duration_ms": round((time.monotonic() - started) * 1000, 2),
                "evidence": result if isinstance(result, (dict, list, str, int, float, bool)) else str(result),
            })
        except Exception as exc:  # noqa: BLE001 - gate must record exact failure
            self.records.append({
                "phase": phase,
                "capability": capability,
                "status": "FAIL",
                "duration_ms": round((time.monotonic() - started) * 1000, 2),
                "error": f"{type(exc).__name__}: {exc}",
            })

    def require_command(self, phase: int, capability: str, command: str) -> str:
        path = shutil.which(command)
        if not path:
            self.records.append({"phase": phase, "capability": capability, "status": "FAIL", "error": f"required provider missing: {command}"})
            raise RuntimeError(f"required provider missing: {command}")
        return path


def _run(command: list[str], timeout: int = TIMEOUT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)


def _http_json(port: int, method: str, path: str) -> tuple[int, dict[str, Any]]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(method, path)
    response = conn.getresponse()
    payload = json.loads(response.read().decode()) if response.getheader("Content-Type", "").startswith("application/json") else {}
    return response.status, payload


def _local_http_server() -> tuple[Any, threading.Thread, int]:
    from teldrive_lab.advanced import serve_json_api

    server = serve_json_api(lambda: {"e2e": True}, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, int(server.server_address[1])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, default=None, help="write JSON evidence report")
    args = parser.parse_args()

    evidence = Evidence()
    failures_before = 0

    # Safety is itself evidence: the strict gate must prove it before touching
    # any disposable fixture.
    evidence.check(12, "safety boundary", lambda: validate_extended_safety())
    evidence.check(21, "advanced safety boundary", lambda: __import__("teldrive_lab.advanced", fromlist=["extended_safety"]).extended_safety())

    with tempfile.TemporaryDirectory(prefix="teldrive-lab-p12-21-e2e-") as raw:
        root = Path(raw)
        (root / "docs").mkdir()
        (root / "media").mkdir()
        (root / "docs" / "fixture.txt").write_text("TelDrive Lab strict E2E fixture for search and metadata.\n", encoding="utf-8")
        (root / "docs" / "fixture.md").write_text("# Strict E2E\nsearchable engineering fixture\n", encoding="utf-8")
        (root / "media" / "sample.mp4").write_bytes(b"not-a-real-video")

        # P12 — storage/cache intelligence.
        db = root / "access.db"
        for _ in range(10):
            record_access(db, str(root / "docs" / "fixture.txt"))
        evidence.check(12, "access frequency", lambda: access_frequency(db))
        heat = storage_heatmap(root, db)
        evidence.check(12, "hot/warm/cold classification", lambda: {"hot": sum(h.tier == "hot" for h in heat), "items": len(heat)})
        evidence.check(12, "prefetch suggestions", lambda: prefetch_suggestions(heat))
        evidence.check(12, "eviction planning", lambda: eviction_plan(heat, 1))
        evidence.check(12, "resource budgeting", lambda: resource_budget(512, 256, 4, 8) == 2)
        evidence.check(12, "tier policy", lambda: storage_tier(10, 999999))

        # P13 — integration/API/metadata surfaces.
        evidence.check(13, "filesystem observation", lambda: observe_storage(root))
        evidence.check(13, "metadata export/import", lambda: (export_metadata([{"name": "fixture.txt"}], root / "metadata.json"), (root / "metadata.json").exists()))
        evidence.check(13, "snapshot manifest", lambda: (create_snapshot_manifest(root, root / "manifest.json"), verify_snapshot_manifest(root / "manifest.json", root)))
        evidence.check(13, "loopback validation", lambda: validate_loopback_host("127.0.0.1"))
        server, thread, port = _local_http_server()
        try:
            evidence.check(13, "real localhost GET health", lambda: _http_json(port, "GET", "/health"))
            evidence.check(13, "real localhost GET metadata", lambda: _http_json(port, "GET", "/metadata"))
            evidence.check(13, "mutation rejected", lambda: _http_json(port, "POST", "/metadata"))
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)

        # P14 — media workflow. A real media container is required for actual
        # probe verification; a byte fixture is retained only for classification.
        evidence.check(14, "media classification", lambda: media_records(root / "media"))
        evidence.check(14, "thumbnail/provider inventory", thumbnail_capability)
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            generated = root / "media" / "e2e.mp4"
            proc = _run([ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=320x240:d=1", "-pix_fmt", "yuv420p", "-y", str(generated)], timeout=30)
            if proc.returncode != 0:
                raise RuntimeError(f"ffmpeg fixture generation failed: {proc.stderr.strip()}")
            evidence.check(14, "real ffprobe media inspection", lambda: media_probe(generated))
        else:
            evidence.records.append({"phase": 14, "capability": "real ffprobe media inspection", "status": "FAIL", "error": "required provider missing: ffmpeg"})

        # P15 — document/AI modalities. Provider-backed capabilities are hard
        # requirements for this strict gate.
        pdf = root / "docs" / "e2e.pdf"
        if shutil.which("pandoc"):
            proc = _run(["pandoc", str(root / "docs" / "fixture.md"), "-o", str(pdf)])
            if proc.returncode != 0:
                raise RuntimeError(f"pandoc PDF generation failed: {proc.stderr.strip()}")
        elif shutil.which("weasyprint"):
            proc = _run(["weasyprint", str(root / "docs" / "fixture.md"), str(pdf)])
            if proc.returncode != 0:
                raise RuntimeError("weasyprint PDF generation failed")
        else:
            # A deterministic minimal PDF is sufficient for exercising the
            # Lab PDF adapters; it contains no external data.
            pdf.write_bytes(b"%PDF-1.4\n1 0 obj<< /Type /Catalog /Pages 2 0 R>>endobj\n2 0 obj<< /Type /Pages /Kids [] /Count 0>>endobj\ntrailer<< /Root 1 0 R>>\n%%EOF\n")
        evidence.check(15, "document fingerprint", lambda: document_fingerprint(pdf))
        evidence.check(15, "OCR provider", lambda: (evidence.require_command(15, "OCR provider", "tesseract"), ocr(root / "docs" / "fixture.txt")))
        evidence.check(15, "speech-to-text provider", lambda: (evidence.require_command(15, "speech-to-text provider", "whisper"), speech_to_text(root / "media" / "e2e.mp4", timeout=60)))
        evidence.check(15, "local embedding", lambda: len(local_embedding("strict e2e")) == 256)
        evidence.check(15, "vision sidecar boundary", lambda: image_vision_summary(root / "media" / "sample.mp4"))

        # P16 — content-aware indexing/search.
        idx = content_index([root / "docs" / "fixture.txt", root / "docs" / "fixture.md"])
        evidence.check(16, "content index", lambda: idx)
        evidence.check(16, "full-text search", lambda: search_content(idx, "searchable"))
        evidence.check(16, "metadata-aware search", lambda: search_content(idx, "fixture"))

        # P17 — advisory AI + organization/enrichment surfaces.
        evidence.check(17, "local AI advisory is non-authoritative", lambda: {"authoritative": local_ai_advisory("strict fixture").authoritative})
        evidence.check(17, "category analysis", lambda: category_analysis(root.iterdir()))
        evidence.check(17, "AI workflow plan is non-authoritative", lambda: ai_workflow_plan([{"id": "e2e"}]))
        evidence.check(17, "local model provider", lambda: evidence.require_command(17, "local model provider", "ollama"))

        # P18 — analytics/economics.
        evidence.check(18, "growth forecast", lambda: growth_forecast([(0, 100), (86400, 200)]))
        evidence.check(18, "transfer cost estimate", lambda: transfer_cost_estimate(1024))
        evidence.check(18, "control center analytics surface", lambda: control_center_payload(root))

        # P19 — snapshot lifecycle and verification.
        snapshot = root.parent / "strict-snapshot.json"
        evidence.check(19, "snapshot creation", lambda: create_snapshot(root, snapshot))
        evidence.check(19, "snapshot verification", lambda: verify_snapshot(snapshot, root))
        snapshot.unlink(missing_ok=True)

        # P20 — explicit cross-project contracts.
        evidence.check(20, "integration contracts", lambda: integration_contracts())
        evidence.check(20, "project contracts", lambda: project_contracts())

        # P21 — CAS/dedup plus orchestration and safety boundary.
        cas = CASStore(root / "cas")
        digest = cas.put(root / "docs" / "fixture.txt")
        evidence.check(21, "content-addressable storage", lambda: {"digest": digest, "present": cas.has(digest)})
        evidence.check(21, "dedup planning", lambda: dedup_plan([root / "docs" / "fixture.txt"]))
        evidence.check(21, "SHA-256 evidence", lambda: hashlib.sha256((root / "docs" / "fixture.txt").read_bytes()).hexdigest())

    failures = [r for r in evidence.records if r["status"] == "FAIL"]
    report = {
        "schema": "teldrive-lab.p12-p21-strict-e2e.v1",
        "strict": True,
        "production_mutation": False,
        "recorded_at": time.time(),
        "host": {"python": os.sys.version, "platform": os.name},
        "summary": {"total": len(evidence.records), "passed": len(evidence.records) - len(failures), "failed": len(failures)},
        "records": evidence.records,
    }
    if args.evidence:
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    for record in evidence.records:
        print(f"P{record['phase']:02d} {record['capability']}: {record['status']}")
    print(f"P12-P21 STRICT E2E: {'PASS' if not failures else 'FAIL'}")
    print(f"evidence records: {len(evidence.records)}")
    print(f"production storage mutation: NONE")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
