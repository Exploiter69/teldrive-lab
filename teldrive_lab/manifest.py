"""Provider-independent durable object manifest.

The manifest is Lab-owned evidence. It contains stable logical identity and
provider references, so Telegram history is never the only catalog.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from .models import FileRecord, VerificationState

MANIFEST_VERSION = 1

@dataclass(frozen=True, slots=True)
class ProviderReference:
    provider_id: str
    object_id: str
    verified: bool = False
    metadata: dict[str, str] = field(default_factory=dict)

@dataclass(frozen=True, slots=True)
class ManifestEntry:
    object_id: str
    logical_path: str
    size: int | None
    sha256: str | None
    verification_state: str
    source_type: str
    source_identifier: str
    created_at: str | None = None
    modified_at: str | None = None
    encryption_class: str = "UNKNOWN"
    provider_references: tuple[ProviderReference, ...] = ()

    @classmethod
    def from_record(cls, record: FileRecord, *, object_id: str | None = None, provider_reference: ProviderReference | None = None) -> "ManifestEntry":
        return cls(
            object_id=object_id or stable_object_id(record), logical_path=record.path, size=record.size,
            sha256=record.sha256, verification_state=record.verification_state.value,
            source_type=record.source_type.value, source_identifier=record.source_identifier,
            created_at=record.created_at, modified_at=record.modified_at,
            encryption_class=record.encryption_class.value,
            provider_references=(provider_reference,) if provider_reference else (),
        )

def stable_object_id(record: FileRecord) -> str:
    import hashlib
    payload = "\x1f".join((record.source_type.value, record.source_identifier, record.path))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

@dataclass(frozen=True, slots=True)
class Manifest:
    entries: tuple[ManifestEntry, ...]
    version: int = MANIFEST_VERSION

    def to_dict(self) -> dict[str, object]:
        return {"manifest_version": self.version, "entries": [
            {**{k: v for k, v in asdict(entry).items() if k != "provider_references"},
             "provider_references": [asdict(ref) for ref in entry.provider_references]}
            for entry in self.entries]}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "Manifest":
        version = int(payload.get("manifest_version", 0))
        if version != MANIFEST_VERSION:
            raise ValueError(f"unsupported manifest version {version}")
        raw_entries = payload.get("entries")
        if not isinstance(raw_entries, list):
            raise ValueError("manifest entries must be a list")
        entries: list[ManifestEntry] = []
        for raw in raw_entries:
            if not isinstance(raw, dict):
                raise ValueError("manifest entry must be an object")
            refs_raw = raw.get("provider_references", [])
            if not isinstance(refs_raw, list):
                raise ValueError("provider_references must be a list")
            refs = tuple(ProviderReference(str(ref["provider_id"]), str(ref["object_id"]), bool(ref.get("verified", False)), {str(k): str(v) for k, v in dict(ref.get("metadata", {})).items()}) for ref in refs_raw if isinstance(ref, dict))
            entries.append(ManifestEntry(
                object_id=str(raw["object_id"]), logical_path=str(raw["logical_path"]),
                size=int(raw["size"]) if raw.get("size") is not None else None,
                sha256=str(raw["sha256"]) if raw.get("sha256") else None,
                verification_state=str(raw["verification_state"]), source_type=str(raw["source_type"]),
                source_identifier=str(raw["source_identifier"]), created_at=str(raw["created_at"]) if raw.get("created_at") else None,
                modified_at=str(raw["modified_at"]) if raw.get("modified_at") else None,
                encryption_class=str(raw.get("encryption_class", "UNKNOWN")), provider_references=refs))
        return cls(tuple(sorted(entries, key=lambda item: (item.logical_path, item.object_id))), version)

    @classmethod
    def from_json(cls, text: str) -> "Manifest":
        payload = json.loads(text)
        if not isinstance(payload, dict): raise ValueError("manifest root must be an object")
        return cls.from_dict(payload)

    def write(self, path: str | Path) -> None:
        target = Path(path); target.parent.mkdir(parents=True, exist_ok=True); target.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def read(cls, path: str | Path) -> "Manifest":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))

def manifest_from_records(records: Iterable[FileRecord]) -> Manifest:
    return Manifest(tuple(sorted((ManifestEntry.from_record(record) for record in records), key=lambda item: (item.logical_path, item.object_id))))

def verified_provider_copies(entry: ManifestEntry) -> tuple[ProviderReference, ...]:
    return tuple(ref for ref in entry.provider_references if ref.verified)

def requires_evacuation(entry: ManifestEntry, unavailable_provider: str) -> bool:
    return entry.verification_state == VerificationState.VERIFIED.value and not any(ref.verified and ref.provider_id != unavailable_provider for ref in entry.provider_references)
