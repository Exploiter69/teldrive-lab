"""Deterministic transfer failure classification for Job Engine retries."""

from __future__ import annotations

from enum import Enum


class TransferErrorClass(str, Enum):
    TRANSIENT = "TRANSIENT"
    RATE_LIMITED = "RATE_LIMITED"
    PERMANENT = "PERMANENT"
    INTEGRITY = "INTEGRITY"


def classify_transfer_error(error: str | None) -> TransferErrorClass:
    text = (error or "").lower()
    if "checksum" in text or "integrity" in text or "mismatch" in text:
        return TransferErrorClass.INTEGRITY
    if any(token in text for token in ("rate limit", "too many requests", "429", "retry-after")):
        return TransferErrorClass.RATE_LIMITED
    if any(token in text for token in ("timeout", "timed out", "temporar", "connection reset", "connection refused", "unavailable", "network")):
        return TransferErrorClass.TRANSIENT
    return TransferErrorClass.PERMANENT
