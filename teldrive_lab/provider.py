"""Provider abstraction and deterministic capability/health semantics.

Stage 3 keeps provider-specific behavior behind a small, dependency-free
contract. Providers never receive policy authority; the Lab owns decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Protocol


class ProviderCapability(StrEnum):
    LIST = "LIST"
    READ = "READ"
    RANGE_READ = "RANGE_READ"
    WRITE = "WRITE"
    DELETE = "DELETE"
    MOVE = "MOVE"
    COPY = "COPY"
    CHECKSUM = "CHECKSUM"
    RESUME = "RESUME"


class ProviderState(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class ProviderErrorClass(StrEnum):
    RATE_LIMITED = "RATE_LIMITED"
    TRANSIENT = "TRANSIENT"
    AUTHENTICATION = "AUTHENTICATION"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    PERMISSION = "PERMISSION"
    UNSUPPORTED = "UNSUPPORTED"
    INVALID = "INVALID"
    PERMANENT = "PERMANENT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ProviderHealth:
    provider_id: str
    state: ProviderState
    capabilities: frozenset[ProviderCapability] = field(default_factory=frozenset)
    latency_ms: float | None = None
    retry_after_seconds: float | None = None
    message: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderError:
    provider_id: str
    classification: ProviderErrorClass
    message: str
    retryable: bool
    retry_after_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class RetryDecision:
    retry: bool
    delay_seconds: float
    attempt: int
    reason: str


class StorageProvider(Protocol):
    """Read/write provider contract; authorization remains outside it."""

    provider_id: str

    def health(self) -> ProviderHealth: ...

    def capabilities(self) -> frozenset[ProviderCapability]: ...


def classify_provider_error(
    provider_id: str,
    error: BaseException | str,
    *,
    retry_after_seconds: float | None = None,
) -> ProviderError:
    """Classify common provider failures without provider-specific dependencies."""
    text = str(error).strip().lower()
    if any(token in text for token in ("flood", "rate limit", "too many requests", "429")):
        return ProviderError(provider_id, ProviderErrorClass.RATE_LIMITED, str(error), True, retry_after_seconds)
    if any(token in text for token in ("timeout", "temporar", "connection reset", "connection refused", "unavailable")):
        return ProviderError(provider_id, ProviderErrorClass.TRANSIENT, str(error), True, retry_after_seconds)
    if any(token in text for token in ("unauthorized", "authentication", "invalid token", "401")):
        return ProviderError(provider_id, ProviderErrorClass.AUTHENTICATION, str(error), False)
    if any(token in text for token in ("forbidden", "permission denied", "403")):
        return ProviderError(provider_id, ProviderErrorClass.PERMISSION, str(error), False)
    if any(token in text for token in ("not found", "404", "missing")):
        return ProviderError(provider_id, ProviderErrorClass.NOT_FOUND, str(error), False)
    if any(token in text for token in ("conflict", "already exists", "409")):
        return ProviderError(provider_id, ProviderErrorClass.CONFLICT, str(error), False)
    if any(token in text for token in ("unsupported", "not implemented")):
        return ProviderError(provider_id, ProviderErrorClass.UNSUPPORTED, str(error), False)
    if any(token in text for token in ("invalid", "bad request", "400")):
        return ProviderError(provider_id, ProviderErrorClass.INVALID, str(error), False)
    return ProviderError(provider_id, ProviderErrorClass.UNKNOWN, str(error), False)


def retry_decision(error: ProviderError, *, attempt: int, max_attempts: int = 5, base_delay_seconds: float = 1.0, max_delay_seconds: float = 300.0) -> RetryDecision:
    """Return a bounded retry decision; never bypasses provider backpressure."""
    if attempt < 1 or max_attempts < 1:
        raise ValueError("attempt and max_attempts must be positive")
    if attempt >= max_attempts or not error.retryable:
        return RetryDecision(False, 0.0, attempt, "retry budget exhausted or failure is non-retryable")
    if base_delay_seconds < 0 or max_delay_seconds < 0:
        raise ValueError("delay limits must be non-negative")
    import math
    exponential = min(max_delay_seconds, base_delay_seconds * math.pow(2, attempt - 1))
    delay = max(exponential, error.retry_after_seconds or 0.0)
    delay = min(delay, max_delay_seconds)
    return RetryDecision(True, delay, attempt, error.classification.value)


def capability_names(capabilities: frozenset[ProviderCapability] | set[ProviderCapability]) -> tuple[str, ...]:
    return tuple(sorted(item.value for item in capabilities))


def health_payload(health: ProviderHealth) -> Mapping[str, object]:
    return {
        "provider_id": health.provider_id,
        "state": health.state.value,
        "capabilities": list(capability_names(health.capabilities)),
        "latency_ms": health.latency_ms,
        "retry_after_seconds": health.retry_after_seconds,
        "message": health.message,
    }
