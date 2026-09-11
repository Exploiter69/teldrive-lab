"""Safe, deterministic one-way archival for TelDrive Lab.

Phase 6 deliberately separates archive planning from authorization and execution.
The default workflow is local source -> approved archive destination. Production
TelDrive/Telegram destinations remain protected by the central safety boundary.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Iterable

from .jobs import Job, JobType
from .models import FileRecord, SourceType
from .retry import RetryClass, RetryPolicy, classify_transfer_error
from .safety import AuthorizationReceipt, Operation, authorize
from .transfer import TransferManager, TransferResult, TransferSpec, sha256_file
from .worker import ExecutionResult, ExecutionStatus


class ArchiveAction(StrEnum):
    COPY = "COPY"
    NOOP = "NOOP"
    DUPLICATE = "DUPLICATE"
    CONFLICT = "CONFLICT"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class ArchivePolicy:
    """Deterministic one-way archive policy."""

    directory: str = "archive"
    require_local_source: bool = True
    require_hash: bool = True

    def destination(self, source: Path, archive_root: Path) -> Path:
        # Preserve only the filename by default. Directory structure can be
        # represented by an explicit policy later; never derive paths from
        # untrusted '..' components.
        name = source.name
        if not name or name in {".", ".."}:
            raise ValueError("invalid archive source filename")
        return archive_root / self.directory / name


@dataclass(frozen=True, slots=True)
class ArchiveCandidate:
    source: str
    destination: str
    size: int
    sha256: str
    source_type: SourceType
    duplicate_of: str | None = None


@dataclass(frozen=True, slots=True)
class ArchiveItem:
    candidate: ArchiveCandidate
    action: ArchiveAction
    reason: str


@dataclass(frozen=True, slots=True)
class ArchivePlan:
    items: tuple[ArchiveItem, ...]
    digest: str

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def copy_count(self) -> int:
        return sum(i.action is ArchiveAction.COPY for i in self.items)

    @property
    def duplicate_count(self) -> int:
        return sum(i.action is ArchiveAction.DUPLICATE for i in self.items)

    @property
    def conflict_count(self) -> int:
        return sum(i.action is ArchiveAction.CONFLICT for i in self.items)

    @property
    def blocked_count(self) -> int:
        return sum(i.action is ArchiveAction.BLOCKED for i in self.items)


class ArchivePlanner:
    """Discover/hash local candidates and produce a stable archive plan."""

    def __init__(self, policy: ArchivePolicy | None = None) -> None:
        self.policy = policy or ArchivePolicy()

    @staticmethod
    def _existing_hashes(records: Iterable[FileRecord]) -> dict[tuple[int, str], str]:
        result: dict[tuple[int, str], str] = {}
        for record in records:
            if record.sha256 and record.size >= 0:
                result[(record.size, record.sha256)] = record.path
        return result

    def plan(
        self,
        records: Iterable[FileRecord],
        *,
        archive_root: str,
        existing_records: Iterable[FileRecord] = (),
    ) -> ArchivePlan:
        archive_root_path = Path(archive_root)
        known = self._existing_hashes(existing_records)
        items: list[ArchiveItem] = []

        for record in sorted(records, key=lambda r: (r.path, r.name, r.id)):
            source = Path(record.path)
            if self.policy.require_local_source and record.source_type is not SourceType.LOCAL:
                candidate = ArchiveCandidate(str(source), "", record.size, record.sha256 or "", record.source_type)
                items.append(ArchiveItem(candidate, ArchiveAction.BLOCKED, "archive source must be LOCAL"))
                continue
            if not source.is_file():
                candidate = ArchiveCandidate(str(source), "", record.size, record.sha256 or "", record.source_type)
                items.append(ArchiveItem(candidate, ArchiveAction.BLOCKED, "archive source is not a regular file"))
                continue

            actual_size = source.stat().st_size
            digest = sha256_file(source) if self.policy.require_hash else (record.sha256 or "")
            destination = self.policy.destination(source, archive_root_path)
            candidate = ArchiveCandidate(str(source), str(destination), actual_size, digest, record.source_type)

            duplicate_path = known.get((actual_size, digest)) if digest else None
            if duplicate_path and Path(duplicate_path).resolve(strict=False) != source.resolve(strict=False):
                candidate = ArchiveCandidate(candidate.source, candidate.destination, candidate.size, candidate.sha256,
                                              candidate.source_type, duplicate_path)
                items.append(ArchiveItem(candidate, ArchiveAction.DUPLICATE,
                                         f"matching size+SHA-256 already known at {duplicate_path}"))
                continue

            if source.resolve(strict=False) == destination.resolve(strict=False):
                items.append(ArchiveItem(candidate, ArchiveAction.NOOP, "source already equals archive destination"))
                continue
            if destination.exists():
                items.append(ArchiveItem(candidate, ArchiveAction.CONFLICT,
                                         "archive destination already exists; planner will not overwrite"))
                continue

            decision = authorize(Operation.TRANSFER, source, destination)
            if decision.allowed:
                items.append(ArchiveItem(candidate, ArchiveAction.COPY, "archive policy approved"))
            elif decision.requires_authorization:
                items.append(ArchiveItem(candidate, ArchiveAction.COPY,
                                         "archive policy approved; explicit authorization required to apply"))
            else:
                items.append(ArchiveItem(candidate, ArchiveAction.BLOCKED, decision.reason))

        canonical = [
            {"source": i.candidate.source, "destination": i.candidate.destination,
             "size": i.candidate.size, "sha256": i.candidate.sha256,
             "source_type": i.candidate.source_type.value, "duplicate_of": i.candidate.duplicate_of,
             "action": i.action.value, "reason": i.reason}
            for i in items
        ]
        payload = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
        return ArchivePlan(tuple(items), hashlib.sha256(payload).hexdigest())


@dataclass(frozen=True, slots=True)
class ArchiveApplyResult:
    plan_digest: str
    results: tuple[TransferResult, ...]

    @property
    def success(self) -> bool:
        return all(result.success for result in self.results)


class ArchiveExecutor:
    """Apply only COPY items through Phase 4, then verify the archive copy."""

    def __init__(self, transfer_manager: TransferManager | None = None) -> None:
        self.transfer_manager = transfer_manager or TransferManager()

    def apply(self, plan: ArchivePlan, *, authorization_id: str = "archive-apply") -> ArchiveApplyResult:
        if plan.blocked_count or plan.conflict_count:
            raise ValueError("archive plan contains blocked or conflicting items")
        if any(i.action is ArchiveAction.DUPLICATE for i in plan.items):
            raise ValueError("archive plan contains duplicate items requiring review")

        results: list[TransferResult] = []
        for item in plan.items:
            if item.action is ArchiveAction.NOOP:
                continue
            if item.action is not ArchiveAction.COPY:
                raise ValueError(f"unsupported archive action: {item.action}")
            receipt = AuthorizationReceipt.for_paths(
                Operation.TRANSFER, item.candidate.source, item.candidate.destination,
                authorization_id=authorization_id,
            )
            result = self.transfer_manager.transfer(
                TransferSpec(item.candidate.source, item.candidate.destination), authorization=receipt
            )
            results.append(result)
            if not result.success or not result.verified:
                break
        return ArchiveApplyResult(plan.digest, tuple(results))


class ArchiveJobExecutor:
    """Durable ARCHIVE job adapter using the Phase 4 transfer boundary."""

    def __init__(self, manager: TransferManager | None = None,
                 retry_policy: RetryPolicy | None = None) -> None:
        self.manager = manager or TransferManager()
        self.retry_policy = retry_policy or RetryPolicy()

    def execute(self, job: Job, authorization: AuthorizationReceipt | None = None) -> ExecutionResult:
        if job.type is not JobType.ARCHIVE:
            return ExecutionResult(ExecutionStatus.PERMANENT, "UNSUPPORTED_JOB_TYPE",
                                   f"archive executor cannot execute {job.type.value}")
        if not job.source or not job.destination:
            return ExecutionResult(ExecutionStatus.PERMANENT, "MISSING_ARCHIVE_PATH",
                                   "archive job requires source and destination")
        if authorization is not None and authorization.operation is not Operation.TRANSFER:
            return ExecutionResult(ExecutionStatus.UNSAFE, "AUTHORIZATION_SCOPE_MISMATCH",
                                   "archive authorization does not match TRANSFER")

        result = self.manager.transfer(TransferSpec(job.source, job.destination), authorization=authorization)
        if result.success and result.verified:
            return ExecutionResult(ExecutionStatus.SUCCESS)
        error = result.error or "archive transfer failed or verification was incomplete"
        if "protected production boundary" in error:
            return ExecutionResult(ExecutionStatus.UNSAFE, "PROTECTED_PRODUCTION", error)
        if "authorization" in error:
            return ExecutionResult(ExecutionStatus.UNSAFE, "UNAUTHORIZED", error)
        if "destination exists" in error or "source is not" in error:
            return ExecutionResult(ExecutionStatus.PERMANENT, "ARCHIVE_INPUT", error)
        code = "VERIFY_MISMATCH" if "checksum mismatch" in error else "ARCHIVE_FAILED"
        category = classify_transfer_error(code)
        if category in (RetryClass.INTEGRITY, RetryClass.TRANSIENT, RetryClass.RATE_LIMITED):
            delay = self.retry_policy.delay(max(1, job.attempts + 1), random_value=0.5)
            return ExecutionResult(ExecutionStatus.RETRYABLE, code, error, delay)
        return ExecutionResult(ExecutionStatus.PERMANENT, code, error)
