"""Bounded, resource-aware concurrency primitives for transfers."""

from __future__ import annotations

import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class TransferLimits:
    max_workers: int = 2
    max_inflight_bytes: int = 256 * 1024 * 1024

    def __post_init__(self) -> None:
        if self.max_workers < 1:
            raise ValueError("max_workers must be >= 1")
        if self.max_inflight_bytes < 1:
            raise ValueError("max_inflight_bytes must be >= 1")


class TransferLimiter:
    """Process-local admission control; it never changes storage configuration."""

    def __init__(self, limits: TransferLimits | None = None) -> None:
        self.limits = limits or TransferLimits()
        self._workers = threading.BoundedSemaphore(self.limits.max_workers)
        self._condition = threading.Condition()
        self._inflight = 0

    def acquire(self, size: int = 0) -> None:
        if size < 0:
            raise ValueError("size must be non-negative")
        self._workers.acquire()
        with self._condition:
            while self._inflight + size > self.limits.max_inflight_bytes:
                self._condition.wait()
            self._inflight += size

    def release(self, size: int = 0) -> None:
        if size < 0:
            raise ValueError("size must be non-negative")
        with self._condition:
            self._inflight = max(0, self._inflight - size)
            self._condition.notify_all()
        self._workers.release()

    @property
    def inflight_bytes(self) -> int:
        with self._condition:
            return self._inflight
