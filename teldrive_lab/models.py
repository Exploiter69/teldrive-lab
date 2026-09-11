"""Canonical metadata models for the TelDrive Lab catalog."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class SourceType(StrEnum):
    LOCAL = "LOCAL"
    TELDRIVE = "TELDRIVE"
    RCLONE = "RCLONE"
    TELEGRAM = "TELEGRAM"
    ARCHIVE = "ARCHIVE"
    BACKUP = "BACKUP"
    UNKNOWN = "UNKNOWN"


class DestinationType(StrEnum):
    LOCAL = "LOCAL"
    RAW = "RAW"
    CRYPT = "CRYPT"
    TELDRIVE = "TELDRIVE"
    BACKUP = "BACKUP"
    QUARANTINE = "QUARANTINE"
    UNKNOWN = "UNKNOWN"


class EncryptionClass(StrEnum):
    RAW = "RAW"
    CRYPT = "CRYPT"
    UNKNOWN = "UNKNOWN"


class HashState(StrEnum):
    UNKNOWN = "UNKNOWN"
    PENDING = "PENDING"
    COMPUTED = "COMPUTED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    STALE = "STALE"


class VerificationState(StrEnum):
    UNVERIFIED = "UNVERIFIED"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    STALE = "STALE"


@dataclass(frozen=True, slots=True)
class FileRecord:
    """One observed object in Lab's derived catalog.

    ``source_type``, ``source_identifier`` and ``path`` form the stable
    observation identity used by the catalog upsert operation.
    """

    path: str
    name: str
    parent_path: str | None
    size: int | None
    mime_type: str | None
    extension: str | None
    created_at: str | None
    modified_at: str | None
    sha256: str | None
    hash_state: HashState
    source_type: SourceType
    source_identifier: str
    destination_type: DestinationType | None
    destination_identifier: str | None
    telegram_file_id: str | None
    telegram_message_id: str | None
    telegram_channel_id: str | None
    encryption_class: EncryptionClass
    verification_state: VerificationState
    tags: tuple[str, ...] | None
    job_id: str | None
    first_seen_at: str
    last_seen_at: str
    id: int | None = None

    @classmethod
    def from_mapping(cls, row: Any) -> "FileRecord":
        """Build a record from a sqlite Row or mapping."""
        tags = row["tags"]
        import json

        parsed_tags = tuple(json.loads(tags)) if tags else None
        return cls(
            id=row["id"],
            path=row["path"],
            name=row["name"],
            parent_path=row["parent_path"],
            size=row["size"],
            mime_type=row["mime_type"],
            extension=row["extension"],
            created_at=row["created_at"],
            modified_at=row["modified_at"],
            sha256=row["sha256"],
            hash_state=HashState(row["hash_state"]),
            source_type=SourceType(row["source_type"]),
            source_identifier=row["source_identifier"],
            destination_type=(DestinationType(row["destination_type"]) if row["destination_type"] else None),
            destination_identifier=row["destination_identifier"],
            telegram_file_id=row["telegram_file_id"],
            telegram_message_id=row["telegram_message_id"],
            telegram_channel_id=row["telegram_channel_id"],
            encryption_class=EncryptionClass(row["encryption_class"]),
            verification_state=VerificationState(row["verification_state"]),
            tags=parsed_tags,
            job_id=row["job_id"],
            first_seen_at=row["first_seen_at"],
            last_seen_at=row["last_seen_at"],
        )
