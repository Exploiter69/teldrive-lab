"""Bounded retry classification and backoff for transfer workflows."""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum


class RetryClass(str, Enum):
    TRANSIENT = "TRANSIENT"
    RATE_LIMITED = "RATE_LIMITED"
    INTEGRITY = "INTEGRITY"
    PERMANENT = "PERMANENT"
    UNSAFE = "UNSAFE"


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay: float = 2.0
    max_delay: float = 60.0
    jitter: float = 0.25

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.base_delay < 0 or self.max_delay < 0:
            raise ValueError("delays must be non-negative")
        if self.max_delay < self.base_delay:
            raise ValueError("max_delay must be >= base_delay")
        if not 0 <= self.jitter <= 1:
            raise ValueError("jitter must be between 0 and 1")

    def delay(self, attempt: int, *, random_value: float | None = None) -> float:
        """Return bounded exponential backoff for a 1-based failed attempt."""
        if attempt < 1:
            raise ValueError("attempt must be >= 1")
        raw = min(self.max_delay, self.base_delay * (2 ** (attempt - 1)))
        if self.jitter == 0:
            return raw
        value = random.random() if random_value is None else random_value
        if not 0 <= value <= 1:
            raise ValueError("random_value must be between 0 and 1")
        factor = 1 - self.jitter + (2 * self.jitter * value)
        return min(self.max_delay, raw * factor)


def classify_transfer_error(error_code: str | None, *, protected: bool = False) -> RetryClass:
    """Classify without guessing from arbitrary exception text."""
    if protected:
        return RetryClass.UNSAFE
    code = (error_code or "").upper()
    if code in {"UNAUTHORIZED", "PROTECTED_PRODUCTION", "UNSAFE_OPERATION", "POLICY_DENIED"}:
        return RetryClass.UNSAFE
    if code in {"TRANSFER_INPUT", "SOURCE_MISSING", "DESTINATION_EXISTS", "UNSUPPORTED"}:
        return RetryClass.PERMANENT
    if code in {"RATE_LIMIT", "RATE_LIMITED", "HTTP_429", "FLOOD_WAIT"}:
        return RetryClass.RATE_LIMITED
    if code in {"VERIFY_MISMATCH", "CHECKSUM_MISMATCH", "INTEGRITY"}:
        return RetryClass.INTEGRITY
    return RetryClass.TRANSIENT
