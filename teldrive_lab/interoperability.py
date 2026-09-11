"""Stage 4 interoperability contracts and report-only planning helpers."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping


class InteropCapability(StrEnum):
    HTTP_READ = "HTTP_READ"
    HTTP_RANGE_READ = "HTTP_RANGE_READ"
    RCLONE = "RCLONE"
    WEB_DAV = "WEB_DAV"
    LOCAL_FILESYSTEM = "LOCAL_FILESYSTEM"
    JELLYFIN = "JELLYFIN"
    WEBHOOK = "WEBHOOK"


@dataclass(frozen=True, slots=True)
class InteropEndpoint:
    endpoint_id: str
    kind: InteropCapability
    read_only: bool = True
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class CapabilityNegotiation:
    provider_id: str
    requested: frozenset[InteropCapability]
    supported: frozenset[InteropCapability]
    accepted: frozenset[InteropCapability]


def negotiate_capabilities(
    provider_id: str,
    requested: frozenset[InteropCapability] | set[InteropCapability],
    supported: frozenset[InteropCapability] | set[InteropCapability],
) -> CapabilityNegotiation:
    req = frozenset(requested)
    sup = frozenset(supported)
    return CapabilityNegotiation(provider_id, req, sup, req & sup)


def endpoint_payload(endpoint: InteropEndpoint) -> Mapping[str, object]:
    return {
        "endpoint_id": endpoint.endpoint_id,
        "kind": endpoint.kind.value,
        "read_only": endpoint.read_only,
        "enabled": endpoint.enabled,
    }


def safe_range(start: int, length: int, *, object_size: int) -> tuple[int, int]:
    """Validate a bounded HTTP-style byte range without touching storage."""
    if start < 0 or length <= 0 or object_size < 0:
        raise ValueError("invalid range")
    if start >= object_size:
        raise ValueError("range starts beyond object")
    end = min(start + length, object_size)
    return start, end


def webhook_event(event_type: str, object_id: str, *, version: int = 1) -> dict[str, object]:
    if not event_type.strip() or not object_id.strip():
        raise ValueError("event_type and object_id are required")
    return {"version": version, "type": event_type, "object_id": object_id}
