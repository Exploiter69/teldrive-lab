"""Deterministic, reviewable organization planning for TelDrive Lab.

The organization engine classifies catalog observations and produces a stable
plan. It never treats classification as authorization and never mutates a
source or destination during planning. Optional application delegates every
copy to the Phase 4 TransferManager with an explicit, scope-bound receipt.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Iterable

from .models import FileRecord
from .safety import AuthorizationReceipt, Operation, authorize
from .transfer import TransferManager, TransferResult, TransferSpec


class FileClass(StrEnum):
    PROJECT = "PROJECT"
    BACKUP = "BACKUP"
    MOVIE = "MOVIE"
    DATASET = "DATASET"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    DOCUMENT = "DOCUMENT"
    ARCHIVE = "ARCHIVE"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class OrganizationAction(StrEnum):
    COPY = "COPY"
    NOOP = "NOOP"
    CONFLICT = "CONFLICT"
    BLOCKED = "BLOCKED"


class StorageClass(StrEnum):
    RAW = "RAW"
    CRYPT = "CRYPT"


@dataclass(frozen=True, slots=True)
class OrganizationRule:
    rule_id: str
    path_prefix: str
    file_class: FileClass
    storage_class: StorageClass


@dataclass(frozen=True, slots=True)
class OrganizationPolicy:
    """Ordered deterministic policy; earlier path rules have precedence."""

    rules: tuple[OrganizationRule, ...] = (
        OrganizationRule("projects", "projects/", FileClass.PROJECT, StorageClass.CRYPT),
        OrganizationRule("backups", "backups/", FileClass.BACKUP, StorageClass.CRYPT),
        OrganizationRule("movies", "movies/", FileClass.MOVIE, StorageClass.RAW),
        OrganizationRule("datasets", "datasets/", FileClass.DATASET, StorageClass.RAW),
    )

    extension_map: tuple[tuple[str, FileClass], ...] = (
        (".jpg", FileClass.IMAGE), (".jpeg", FileClass.IMAGE), (".png", FileClass.IMAGE),
        (".gif", FileClass.IMAGE), (".webp", FileClass.IMAGE), (".heic", FileClass.IMAGE),
        (".mp4", FileClass.VIDEO), (".mkv", FileClass.VIDEO), (".webm", FileClass.VIDEO),
        (".mov", FileClass.VIDEO), (".avi", FileClass.VIDEO),
        (".mp3", FileClass.AUDIO), (".flac", FileClass.AUDIO), (".wav", FileClass.AUDIO),
        (".m4a", FileClass.AUDIO), (".ogg", FileClass.AUDIO),
        (".pdf", FileClass.DOCUMENT), (".txt", FileClass.DOCUMENT), (".md", FileClass.DOCUMENT),
        (".doc", FileClass.DOCUMENT), (".docx", FileClass.DOCUMENT), (".xls", FileClass.DOCUMENT),
        (".xlsx", FileClass.DOCUMENT), (".ppt", FileClass.DOCUMENT), (".pptx", FileClass.DOCUMENT),
        (".zip", FileClass.ARCHIVE), (".tar", FileClass.ARCHIVE), (".gz", FileClass.ARCHIVE),
        (".7z", FileClass.ARCHIVE), (".rar", FileClass.ARCHIVE),
    )

    def classify(self, record: FileRecord) -> tuple[FileClass, StorageClass, str]:
        normalized = record.path.replace("\\", "/").casefold().strip("/")
        segments = tuple(segment for segment in normalized.split("/") if segment)
        for rule in self.rules:
            prefix_segments = tuple(segment for segment in rule.path_prefix.replace("\\", "/").casefold().strip("/").split("/") if segment)
            if prefix_segments and any(
                segments[index:index + len(prefix_segments)] == prefix_segments
                for index in range(len(segments) - len(prefix_segments) + 1)
            ):
                return rule.file_class, rule.storage_class, rule.rule_id

        extension = (record.extension or Path(record.name).suffix).casefold()
        for candidate, file_class in self.extension_map:
            if extension == candidate:
                return file_class, StorageClass.RAW, f"extension:{candidate}"

        mime = (record.mime_type or mimetypes.guess_type(record.name)[0] or "").casefold()
        if mime.startswith("image/"):
            return FileClass.IMAGE, StorageClass.RAW, "mime:image"
        if mime.startswith("video/"):
            return FileClass.VIDEO, StorageClass.RAW, "mime:video"
        if mime.startswith("audio/"):
            return FileClass.AUDIO, StorageClass.RAW, "mime:audio"
        if mime.startswith("text/") or mime == "application/pdf":
            return FileClass.DOCUMENT, StorageClass.RAW, "mime:document"
        return FileClass.UNKNOWN, StorageClass.RAW, "fallback:unknown"


def _safe_relative_name(record: FileRecord) -> str:
    """Return a deterministic, traversal-safe relative source name."""
    name = Path(record.name).name
    if not name or name in {".", ".."}:
        raise ValueError("record has an invalid filename")
    return name


@dataclass(frozen=True, slots=True)
class OrganizationItem:
    source: str
    destination: str
    file_class: FileClass
    storage_class: StorageClass
    rule_id: str
    action: OrganizationAction
    reason: str


@dataclass(frozen=True, slots=True)
class OrganizationPlan:
    items: tuple[OrganizationItem, ...]
    digest: str

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def copy_count(self) -> int:
        return sum(item.action is OrganizationAction.COPY for item in self.items)

    @property
    def conflict_count(self) -> int:
        return sum(item.action is OrganizationAction.CONFLICT for item in self.items)

    @property
    def blocked_count(self) -> int:
        return sum(item.action is OrganizationAction.BLOCKED for item in self.items)

    @property
    def noop_count(self) -> int:
        return sum(item.action is OrganizationAction.NOOP for item in self.items)


class OrganizationPlanner:
    """Build stable plans from metadata without mutating the filesystem."""

    def __init__(self, policy: OrganizationPolicy | None = None) -> None:
        self.policy = policy or OrganizationPolicy()

    def plan(self, records: Iterable[FileRecord], *, raw_root: str, crypt_root: str) -> OrganizationPlan:
        items: list[OrganizationItem] = []
        for record in sorted(records, key=lambda value: (value.path, value.name)):
            file_class, storage_class, rule_id = self.policy.classify(record)
            root = Path(crypt_root if storage_class is StorageClass.CRYPT else raw_root)
            destination = root / file_class.value.lower() / _safe_relative_name(record)
            source = Path(record.path)

            if source.resolve(strict=False) == destination.resolve(strict=False):
                action = OrganizationAction.NOOP
                reason = "source already equals deterministic destination"
            elif destination.exists():
                action = OrganizationAction.CONFLICT
                reason = "destination already exists; planner will not overwrite"
            else:
                decision = authorize(Operation.TRANSFER, source, destination)
                if not decision.allowed:
                    action = OrganizationAction.BLOCKED
                    reason = decision.reason
                else:
                    action = OrganizationAction.COPY
                    reason = "deterministic policy match"

            items.append(OrganizationItem(
                source=str(source), destination=str(destination), file_class=file_class,
                storage_class=storage_class, rule_id=rule_id, action=action, reason=reason,
            ))

        canonical = [
            {
                "source": item.source,
                "destination": item.destination,
                "file_class": item.file_class.value,
                "storage_class": item.storage_class.value,
                "rule_id": item.rule_id,
                "action": item.action.value,
                "reason": item.reason,
            }
            for item in items
        ]
        payload = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
        return OrganizationPlan(tuple(items), hashlib.sha256(payload).hexdigest())


@dataclass(frozen=True, slots=True)
class OrganizationApplyResult:
    plan_digest: str
    results: tuple[TransferResult, ...]

    @property
    def success(self) -> bool:
        return all(result.success for result in self.results)


class OrganizationExecutor:
    """Apply only COPY items through the Phase 4 transfer boundary."""

    def __init__(self, transfer_manager: TransferManager | None = None) -> None:
        self.transfer_manager = transfer_manager or TransferManager()

    def apply(self, plan: OrganizationPlan, *, authorization_id: str = "organization-apply") -> OrganizationApplyResult:
        if plan.blocked_count or plan.conflict_count:
            raise ValueError("organization plan contains blocked or conflicting items")
        results: list[TransferResult] = []
        for item in plan.items:
            if item.action is OrganizationAction.NOOP:
                continue
            if item.action is not OrganizationAction.COPY:
                raise ValueError(f"unsupported plan action: {item.action}")
            receipt = AuthorizationReceipt.for_paths(
                Operation.TRANSFER, item.source, item.destination, authorization_id=authorization_id
            )
            result = self.transfer_manager.transfer(
                TransferSpec(item.source, item.destination), authorization=receipt
            )
            results.append(result)
            if not result.success:
                break
        return OrganizationApplyResult(plan.digest, tuple(results))
