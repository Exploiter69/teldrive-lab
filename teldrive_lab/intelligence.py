"""Stage 7 intelligence: deterministic first, optional AI advisory only.

The module is deliberately lightweight for the primary i5/8 GB environment. Core
search, explanations, recommendations, and indexing work without an LLM. Optional
local tools (Tesseract/Whisper/Ollama) are capability-gated and never authorize or
execute storage mutations.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable, Sequence

SCHEMA = "teldrive-lab.intelligence.v1"
TEXT_EXTENSIONS = {".txt", ".md", ".rst", ".csv", ".json", ".yaml", ".yml", ".log"}
MEDIA_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".mp3", ".flac", ".wav", ".m4a", ".ogg", ".opus"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff", ".bmp"}


@dataclass(frozen=True)
class SearchResult:
    path: str
    score: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class IntelligenceProposal:
    action: str
    target: str
    rationale: str
    confidence: float
    authoritative: bool = False
    requires_policy: bool = True
    requires_authorization: bool = True


def _tokens(text: str) -> list[str]:
    return re.findall(r"[\w.-]+", text.casefold())


def _run_optional(command: list[str], timeout: int) -> tuple[bool, str]:
    try:
        p = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except (FileNotFoundError, subprocess.SubprocessError):
        return False, ""
    return p.returncode == 0, p.stdout


def capability_report() -> dict[str, Any]:
    return {
        "tesseract": shutil.which("tesseract") is not None,
        "whisper": shutil.which("whisper") is not None,
        "ollama": shutil.which("ollama") is not None,
        "llama_cpp": shutil.which("llama-cli") is not None,
        "core_requires_ai": False,
        "authority": "advisory",
    }


def metadata_index(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Build a rebuildable deterministic metadata/text index in memory."""
    docs: list[dict[str, Any]] = []
    for record in records:
        item = dict(record)
        text = " ".join(str(item.get(k, "")) for k in ("path", "name", "extension", "mime", "title", "tags", "text"))
        item["_tokens"] = _tokens(text)
        docs.append(item)
    return {"schema": SCHEMA, "records": docs, "count": len(docs)}


def _field_text(record: dict[str, Any]) -> str:
    return " ".join(str(record.get(k, "")) for k in ("path", "name", "extension", "mime", "title", "tags", "text", "ocr_text", "transcript"))


def search_metadata(
    index: dict[str, Any],
    query: str,
    *,
    extension: str | None = None,
    min_size: int | None = None,
    max_size: int | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Lexical retrieval with metadata filters and deterministic field-aware scoring."""
    q = _tokens(query)
    results: list[SearchResult] = []
    stopwords = {"a", "an", "and", "find", "for", "in", "of", "the", "to", "with"}
    q = [token for token in q if token not in stopwords]
    for record in index.get("records", []):
        ext = str(record.get("extension", "")).casefold()
        size = int(record.get("size", 0) or 0)
        if extension and ext != extension.casefold():
            continue
        if min_size is not None and size < min_size:
            continue
        if max_size is not None and size > max_size:
            continue
        fields = _field_text(record).casefold()
        tokens = _tokens(fields)
        name = str(record.get("name", "")).casefold()
        path = str(record.get("path", "")).casefold()
        title = str(record.get("title", "")).casefold()
        text = str(record.get("text", "")).casefold()
        ocr_text = str(record.get("ocr_text", "")).casefold()
        transcript = str(record.get("transcript", "")).casefold()
        score = 0.0
        reasons: list[str] = []
        for token in q:
            if token in tokens:
                score += 1.0
                reasons.append(f"token:{token}")
            if token in name:
                score += 2.0
                reasons.append(f"name:{token}")
            if token in path:
                score += 1.0
                reasons.append(f"path:{token}")
            if token in title:
                score += 3.0
                reasons.append(f"title:{token}")
            if token in text or token in ocr_text or token in transcript:
                score += 1.5
                reasons.append(f"content:{token}")
        if q and all(token in title for token in q):
            score += 4.0
            reasons.append("exact_title_phrase")
        if q and all(token in name for token in q):
            score += 3.0
            reasons.append("exact_name_phrase")
        if not q:
            score = 1.0
        if score > 0:
            results.append(SearchResult(str(record.get("path", "")), score, tuple(sorted(set(reasons)))))
    by_path = {str(r.get("path", "")): r for r in index.get("records", [])}
    return [
        {**by_path[x.path], "score": round(x.score, 6), "reasons": list(x.reasons)}
        for x in sorted(results, key=lambda x: (-x.score, x.path))[:limit]
    ]


def structured_filter(
    records: Iterable[dict[str, Any]],
    *,
    extensions: Sequence[str] = (),
    min_size: int | None = None,
    max_size: int | None = None,
    name_pattern: str | None = None,
) -> list[dict[str, Any]]:
    pattern = re.compile(name_pattern, re.I) if name_pattern else None
    allowed = {e.casefold() for e in extensions}
    out = []
    for record in records:
        ext = str(record.get("extension", "")).casefold()
        size = int(record.get("size", 0) or 0)
        name = str(record.get("name", record.get("path", "")))
        if allowed and ext not in allowed:
            continue
        if min_size is not None and size < min_size:
            continue
        if max_size is not None and size > max_size:
            continue
        if pattern and not pattern.search(name):
            continue
        out.append(dict(record))
    return sorted(out, key=lambda r: str(r.get("path", "")))


def parse_natural_language_query(query: str) -> dict[str, Any]:
    """Small deterministic NL parser; it never calls a model."""
    text = query.casefold()
    ext = None
    match = re.search(r"\.(mp4|mkv|webm|mov|avi|mp3|flac|wav|pdf|txt|md|srt|vtt)\b", text)
    if match:
        ext = "." + match.group(1)
    if "video" in text:
        ext = ext or "media-video"
    if "document" in text or "pdf" in text:
        ext = ext or ".pdf"
    size_min = None
    size_match = re.search(r"(?:over|larger than|above)\s+(\d+(?:\.\d+)?)\s*(gb|mb|kb)", text)
    if size_match:
        units = {"kb": 1024, "mb": 1024**2, "gb": 1024**3}
        size_min = int(float(size_match.group(1)) * units[size_match.group(2)])
    return {"query": query, "extension": ext, "min_size": size_min, "filters_deterministic": True}


def natural_language_search(query: str, index: dict[str, Any], *, limit: int = 20) -> list[dict[str, Any]]:
    parsed = parse_natural_language_query(query)
    extension = parsed["extension"] if parsed["extension"] and parsed["extension"].startswith(".") else None
    return search_metadata(index, query, extension=extension, min_size=parsed["min_size"], limit=limit)


def _digest_record(record: dict[str, Any]) -> tuple[str, int]:
    digest = str(record.get("sha256", ""))
    size = int(record.get("size", 0) or 0)
    if digest:
        return digest, size
    return "", size


def duplicate_explanations(records: Iterable[dict[str, Any]]) -> list[IntelligenceProposal]:
    groups: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for record in records:
        digest, size = _digest_record(record)
        if digest:
            groups.setdefault((digest, size), []).append(dict(record))
    out = []
    for (digest, size), copies in sorted(groups.items()):
        if len(copies) < 2:
            continue
        target = ", ".join(sorted(str(r.get("path", r.get("name", "item"))) for r in copies))
        out.append(IntelligenceProposal("REVIEW_DUPLICATES", target, f"{len(copies)} verified copies share SHA-256 {digest[:12]} and size {size} bytes; no deletion is implied", .98))
    return out


def anomaly_explanations(records: Iterable[dict[str, Any]], *, large_file_bytes: int = 10 * 1024**3) -> list[IntelligenceProposal]:
    out: list[IntelligenceProposal] = []
    for record in records:
        path = str(record.get("path", record.get("name", "item")))
        size = int(record.get("size", 0) or 0)
        if record.get("integrity_state") in {"FAILED", "UNVERIFIED"}:
            out.append(IntelligenceProposal("VERIFY", path, "Integrity evidence is missing or failed; verification should precede any lifecycle decision", .99))
        if size >= large_file_bytes:
            out.append(IntelligenceProposal("REVIEW_LARGE_OBJECT", path, f"Object is {size} bytes and deserves explicit transfer/cache planning", .85))
    return out


def organization_suggestions(records: Iterable[dict[str, Any]]) -> list[IntelligenceProposal]:
    out = []
    for record in records:
        path = str(record.get("path", record.get("name", "item")))
        ext = str(record.get("extension", "")).casefold()
        if ext in MEDIA_EXTENSIONS:
            category = "media"
        elif ext in IMAGE_EXTENSIONS:
            category = "images"
        elif ext in {".pdf", ".docx", ".txt", ".md", ".rst"}:
            category = "documents"
        elif ext in {".srt", ".vtt", ".ass", ".ssa"}:
            category = "subtitles"
        else:
            continue
        out.append(IntelligenceProposal("SUGGEST_CATEGORY", path, f"Extension {ext or '[none]'} matches the {category} category", .75))
    return out


def metadata_enrichment_suggestions(records: Iterable[dict[str, Any]]) -> list[IntelligenceProposal]:
    out = []
    for record in records:
        path = str(record.get("path", record.get("name", "item")))
        missing = [k for k in ("title", "mime") if not record.get(k)]
        if missing:
            out.append(IntelligenceProposal("ENRICH_METADATA", path, "Missing deterministic metadata: " + ", ".join(missing), .8))
    return out


def recommendation_report(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    records = list(records)
    suggestions = organization_suggestions(records) + metadata_enrichment_suggestions(records) + anomaly_explanations(records)
    return {
        "schema": SCHEMA,
        "recommendations": [asdict(x) for x in suggestions],
        "authority": "advisory",
        "mutation": "NONE",
    }


def ocr_index(path: Path, *, language: str = "eng", max_chars: int = 2_000_000, timeout: int = 60) -> dict[str, Any]:
    if shutil.which("tesseract") is None:
        return {"available": False, "path": str(path), "text": "", "reason": "tesseract_unavailable"}
    ok, text = _run_optional(["tesseract", str(path), "stdout", "-l", language], timeout)
    return {"available": ok, "path": str(path), "text": text[:max_chars], "tool": "tesseract"}


def transcript_index(path: Path, *, model: str = "tiny", timeout: int = 120) -> dict[str, Any]:
    """Use Whisper only when explicitly installed; tiny is the low-resource default."""
    if shutil.which("whisper") is None:
        return {"available": False, "path": str(path), "text": "", "reason": "whisper_unavailable"}
    output_dir = path.parent / ".teldrive-lab-transcripts"
    output_dir.mkdir(parents=True, exist_ok=True)
    ok, _ = _run_optional(["whisper", str(path), "--model", model, "--output_format", "txt", "--output_dir", str(output_dir)], timeout)
    transcript = output_dir / f"{path.stem}.txt"
    return {"available": ok and transcript.exists(), "path": str(path), "text": transcript.read_text(encoding="utf-8", errors="replace") if transcript.exists() else "", "tool": "whisper", "model": model}


def summarize_text(text: str, *, max_sentences: int = 4) -> dict[str, Any]:
    """Extractive, zero-LLM summary for documents/transcripts."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    selected = sentences[:max_sentences]
    return {"summary": " ".join(selected), "method": "extractive_deterministic", "ai_used": False, "sentences": len(selected)}


def ai_proposal(action: str, target: str, rationale: str, confidence: float = .5) -> IntelligenceProposal:
    return IntelligenceProposal(action, target, rationale, max(0.0, min(1.0, confidence)))


def local_model_adapter(prompt: str, *, model: str = "", host: str = "127.0.0.1", port: int = 11434, timeout: int = 30) -> dict[str, Any]:
    """Optional Ollama adapter. It is never invoked by deterministic core paths."""
    if not model:
        return {"available": False, "reason": "model_not_selected", "authority": "advisory"}
    try:
        import http.client
        body = json.dumps({"model": model, "prompt": prompt, "stream": False})
        conn = http.client.HTTPConnection(host, port, timeout=timeout)
        conn.request("POST", "/api/generate", body, {"Content-Type": "application/json"})
        response = conn.getresponse()
        data = json.loads(response.read().decode("utf-8"))
        if response.status >= 400:
            return {"available": False, "reason": f"http_{response.status}", "authority": "advisory"}
        return {"available": True, "response": str(data.get("response", "")), "model": model, "authority": "advisory"}
    except (OSError, ValueError, json.JSONDecodeError):
        return {"available": False, "reason": "local_model_unavailable", "authority": "advisory"}


def export_intelligence(index: dict[str, Any], destination: Path) -> dict[str, Any]:
    payload = {"schema": SCHEMA, "records": index.get("records", [])}
    for record in payload["records"]:
        record.pop("_tokens", None)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["digest"] = hashlib.sha256(canonical.encode()).hexdigest()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return {"path": str(destination), "records": len(payload["records"]), "digest": payload["digest"], "schema": SCHEMA}


def assert_advisory(proposals: Iterable[IntelligenceProposal]) -> None:
    for proposal in proposals:
        if proposal.authoritative or not proposal.requires_policy or not proposal.requires_authorization:
            raise ValueError("intelligence proposal cannot bypass policy/authorization")


__all__ = [
    "SCHEMA", "SearchResult", "IntelligenceProposal", "capability_report", "metadata_index", "search_metadata",
    "structured_filter", "parse_natural_language_query", "natural_language_search", "duplicate_explanations",
    "anomaly_explanations", "organization_suggestions", "metadata_enrichment_suggestions", "recommendation_report",
    "ocr_index", "transcript_index", "summarize_text", "ai_proposal", "local_model_adapter", "export_intelligence",
    "assert_advisory",
]
