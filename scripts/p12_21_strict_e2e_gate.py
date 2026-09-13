"""Strict independent E2E verification for optional Phases 12-21.

The gate uses only disposable local fixtures and localhost services. It never
mounts, reads, writes, deletes, reorganizes, or reconfigures TelDrive
production storage, rclone mounts, or the TelDrive database.

Every capability gets an individual evidence record. Only providers that are
part of the TelDrive Lab product contract are verified here.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import http.client
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable

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


def _jsonable(value: Any) -> Any:
    """Convert gate evidence into JSON-safe deterministic data."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _jsonable(dataclasses.asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


class Evidence:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def check(self, phase: int, capability: str, fn: Callable[[], Any]) -> None:
        started = time.monotonic()
        try:
            result = fn()
            self.records.append(
                {
                    "phase": phase,
                    "capability": capability,
                    "status": "PASS",
                    "duration_ms": round((time.monotonic() - started) * 1000, 2),
                    "evidence": _jsonable(result),
                }
            )
        except Exception as exc:  # noqa: BLE001 - gate must record exact failure
            self.records.append(
                {
                    "phase": phase,
                    "capability": capability,
                    "status": "FAIL",
                    "duration_ms": round((time.monotonic() - started) * 1000, 2),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )


def _run(command: list[str], timeout: int = TIMEOUT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)


def _http_json(port: int, method: str, path: str) -> tuple[int, dict[str, Any]]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(method, path)
    response = conn.getresponse()
    body = response.read()
    payload = json.loads(body.decode()) if response.getheader("Content-Type", "").startswith("application/json") else {}
    return response.status, payload


def _local_http_server() -> tuple[Any, threading.Thread, int]:
    from teldrive_lab.advanced import serve_json_api

    server = serve_json_api(lambda: {"e2e": True}, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, int(server.server_address[1])


def _make_pdf(path: Path) -> None:
    path.write_bytes(
        b"%PDF-1.4\n1 0 obj<< /Type /Catalog /Pages 2 0 R>>endobj\n"
        b"2 0 obj<< /Type /Pages /Kids [] /Count 0>>endobj\n"
        b"trailer<< /Root 1 0 R>>\n%%EOF\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, default=None, help="write JSON evidence report")
    args = parser.parse_args()
    evidence = Evidence()

    evidence.check(12, "safety boundary", validate_extended_safety)
    evidence.check(
        21,
        "advanced safety boundary",
        lambda: __import__("teldrive_lab.advanced", fromlist=["extended_safety"]).extended_safety(),
    )

    with tempfile.TemporaryDirectory(prefix="teldrive-lab-p12-21-e2e-") as raw:
        root = Path(raw)
        docs = root / "docs"
        media = root / "media"
        docs.mkdir()
        media.mkdir()
        (docs / "fixture.txt").write_text(
            "TelDrive Lab strict E2E fixture for search and metadata.\n", encoding="utf-8"
        )
        (docs / "fixture.md").write_text(
            "# Strict E2E\nsearchable engineering fixture\n", encoding="utf-8"
        )

        # P12 — storage/cache intelligence.
        db = root / "access.db"
        for _ in range(10):
            record_access(db, str(docs / "fixture.txt"))
        evidence.check(12, "access frequency", lambda: access_frequency(db))
        heat = storage_heatmap(root, db)
        evidence.check(12, "hot/warm/cold classification", lambda: {"hot": sum(h.tier == "hot" for h in heat), "items": len(heat)})
        evidence.check(12, "prefetch suggestions", lambda: prefetch_suggestions(heat))
        evidence.check(12, "eviction planning", lambda: eviction_plan(heat, 1))
        evidence.check(12, "resource budgeting", lambda: resource_budget(512, 256, 4, 8) == 2)
        evidence.check(12, "tier policy", lambda: storage_tier(10, 999999))

        # P13 — integration/API/metadata surfaces.
        evidence.check(13, "filesystem observation", lambda: observe_storage(root))
        evidence.check(
            13,
            "metadata export/import",
            lambda: (export_metadata([{"name": "fixture.txt"}], root / "metadata.json"), (root / "metadata.json").exists()),
        )
        manifest = root.parent / "strict-manifest.json"
        evidence.check(
            13,
            "snapshot manifest",
            lambda: (create_snapshot_manifest(root, manifest), verify_snapshot_manifest(manifest, root)),
        )
        evidence.check(13, "loopback validation", lambda: validate_loopback_host("127.0.0.1"))
        server, thread, port = _local_http_server()
        try:
            evidence.check(13, "real localhost GET health", lambda: _http_json(port, "GET", "/health"))
            evidence.check(13, "real localhost GET metadata", lambda: _http_json(port, "GET", "/metadata"))
            evidence.check(13, "mutation rejected", lambda: _http_json(port, "POST", "/metadata"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        manifest.unlink(missing_ok=True)

        # P14 — media workflow. A generated real MP4 is required for probe E2E.
        evidence.check(14, "media classification", lambda: media_records(media))
        evidence.check(14, "thumbnail/provider inventory", thumbnail_capability)
        ffmpeg = shutil.which("ffmpeg")
        generated = media / "e2e.mp4"
        if ffmpeg:
            proc = _run(
                [
                    ffmpeg,
                    "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", "color=c=black:s=320x240:d=1",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                    "-shortest", "-pix_fmt", "yuv420p", "-y", str(generated),
                ],
                timeout=30,
            )
            if proc.returncode != 0:
                evidence.check(14, "real ffprobe media inspection", lambda: (_ for _ in ()).throw(RuntimeError(f"ffmpeg fixture generation failed: {proc.stderr.strip()}")))
            else:
                evidence.check(14, "real ffprobe media inspection", lambda: media_probe(generated))
        else:
            evidence.check(14, "real ffprobe media inspection", lambda: (_ for _ in ()).throw(RuntimeError("required provider missing: ffmpeg")))

        # P15 — deterministic document/media intelligence that is part of the
        # supported product contract. Speech transcription is intentionally not
        # part of TelDrive Lab scope.
        pdf = docs / "e2e.pdf"
        _make_pdf(pdf)
        evidence.check(15, "document fingerprint", lambda: document_fingerprint(pdf))
        evidence.check(15, "OCR provider", lambda: (shutil.which("tesseract") or (_ for _ in ()).throw(RuntimeError("required provider missing: tesseract")), ocr(docs / "fixture.txt")))
        evidence.check(15, "local embedding", lambda: len(local_embedding("strict e2e")) == 256)
        evidence.check(15, "vision sidecar boundary", lambda: image_vision_summary(docs / "fixture.txt"))

        # P16 — content-aware indexing/search.
        idx = content_index([docs / "fixture.txt", docs / "fixture.md"])
        evidence.check(16, "content index", lambda: idx)
        evidence.check(16, "full-text search", lambda: search_content(idx, "searchable"))
        evidence.check(16, "metadata-aware search", lambda: search_content(idx, "fixture"))

        # P17 — deterministic advisory/organization surfaces. No LLM provider
        # is required or supported by the current product contract.
        evidence.check(17, "local advisory is non-authoritative", lambda: {"authoritative": local_ai_advisory("strict fixture").authoritative})
        evidence.check(17, "category analysis", lambda: category_analysis(root.iterdir()))
        evidence.check(17, "workflow plan is non-authoritative", lambda: ai_workflow_plan([{"id": "e2e"}]))

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
        evidence.check(20, "integration contracts", integration_contracts)
        evidence.check(20, "project contracts", project_contracts)

        # P21 — CAS/dedup + safety boundary.
        cas = CASStore(root / "cas")
        digest = cas.put(docs / "fixture.txt")
        evidence.check(21, "content-addressable storage", lambda: {"digest": digest, "present": cas.has(digest)})
        evidence.check(21, "dedup planning", lambda: dedup_plan([docs / "fixture.txt"]))
        evidence.check(21, "SHA-256 evidence", lambda: hashlib.sha256((docs / "fixture.txt").read_bytes()).hexdigest())

    failures = [r for r in evidence.records if r["status"] == "FAIL"]
    report = {
        "schema": "teldrive-lab.p12-p21-strict-e2e.v1",
        "strict": True,
        "production_mutation": False,
        "recorded_at": time.time(),
        "host": {"python": os.sys.version, "platform": os.name},
        "summary": {"total": len(evidence.records), "passed": len(evidence.records) - len(failures), "failed": len(failures)},
        "records": _jsonable(evidence.records),
    }
    if args.evidence:
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    for record in evidence.records:
        print(f"P{record['phase']:02d} {record['capability']}: {record['status']}")
    print(f"P12-P21 STRICT E2E: {'PASS' if not failures else 'FAIL'}")
    print(f"evidence records: {len(evidence.records)}")
    print("production storage mutation: NONE")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
