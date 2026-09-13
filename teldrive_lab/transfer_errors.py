"""Compatibility shim for the canonical retry classifier.

New code should import from :mod:`teldrive_lab.retry`. This module remains only
to preserve the existing Phase 4 test/API surface while R0 removes duplicate
retry/error implementations.
"""

from __future__ import annotations

from teldrive_lab.retry import RetryClass

TransferErrorClass = RetryClass


def classify_transfer_error(error: str | None) -> TransferErrorClass:
    """Compatibility wrapper using the canonical error-code classifier."""
    text = (error or "").lower()
    if "checksum" in text or "integrity" in text or "mismatch" in text:
        return RetryClass.INTEGRITY
    if any(token in text for token in ("rate limit", "too many requests", "429", "retry-after")):
        return RetryClass.RATE_LIMITED
    if any(
        token in text
        for token in ("timeout", "timed out", "temporar", "connection reset", "connection refused", "unavailable", "network")
    ):
        return RetryClass.TRANSIENT
    if any(token in text for token in ("unauthorized", "protected", "unsafe", "policy denied")):
        return RetryClass.UNSAFE
    return RetryClass.PERMANENT
