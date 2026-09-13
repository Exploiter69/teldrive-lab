"""Bounded, deterministic filesystem primitives for TelDrive Lab.

These helpers are intentionally Lab-owned. They do not authorize or mutate
TelDrive production storage. Traversal is bounded and symlinks are not followed
by default; file content is read in fixed-size chunks.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Iterator


class ResourceLimitError(RuntimeError):
    """Raised when a bounded filesystem operation exceeds its configured limit."""


DEFAULT_MAX_DEPTH = 64
DEFAULT_MAX_FILES = 100_000
DEFAULT_CHUNK_SIZE = 1024 * 1024
DEFAULT_SAMPLE_BYTES = 2_000_000


def _root(path: Path) -> Path:
    return path.expanduser().resolve()


def _within(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root)
        return True
    except ValueError:
        return False


def iter_files(
    root: Path,
    *,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_files: int = DEFAULT_MAX_FILES,
    follow_symlinks: bool = False,
) -> Iterator[Path]:
    """Yield files in deterministic order with explicit traversal bounds."""
    base = _root(root)
    if max_depth < 0 or max_files < 0:
        raise ValueError("resource limits must be non-negative")
    if not base.exists():
        return
    if not base.is_dir():
        raise NotADirectoryError(base)

    count = 0
    stack: list[tuple[Path, int]] = [(base, 0)]
    while stack:
        directory, depth = stack.pop()
        try:
            entries = sorted(directory.iterdir(), key=lambda p: p.name)
        except OSError:
            continue
        children: list[tuple[Path, int]] = []
        for entry in entries:
            try:
                is_link = entry.is_symlink()
                if is_link and not follow_symlinks:
                    if entry.is_file():
                        # A symlink to a file is deliberately ignored by default.
                        continue
                    continue
                resolved = entry.resolve()
                if not _within(base, resolved):
                    continue
                if entry.is_dir():
                    if depth < max_depth:
                        children.append((resolved, depth + 1))
                    elif depth == max_depth:
                        # A directory below the configured boundary is only a
                        # limit violation when it contains an entry we would scan.
                        try:
                            if any(entry.iterdir()):
                                raise ResourceLimitError(
                                    f"maximum traversal depth exceeded at {entry} (max_depth={max_depth})"
                                )
                        except ResourceLimitError:
                            raise
                        except OSError:
                            continue
                elif entry.is_file():
                    count += 1
                    if count > max_files:
                        raise ResourceLimitError(
                            f"maximum file count exceeded (max_files={max_files})"
                        )
                    yield resolved
            except ResourceLimitError:
                raise
            except OSError:
                continue
        # Reverse because stack is LIFO and we want lexical traversal order.
        stack.extend(reversed(children))


def stream_sha256(path: Path, *, chunk_size: int = DEFAULT_CHUNK_SIZE) -> tuple[str, int]:
    """Return SHA-256 and byte count without loading the file into memory."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def bounded_sample(path: Path, max_bytes: int = DEFAULT_SAMPLE_BYTES) -> bytes:
    """Read at most ``max_bytes`` from a file."""
    if max_bytes < 0:
        raise ValueError("max_bytes must be non-negative")
    with path.open("rb") as handle:
        return handle.read(max_bytes)


def copy_stream(
    source: Path,
    destination: Path,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> tuple[str, int]:
    """Stream-copy a file and return its SHA-256 and byte count."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    digest = hashlib.sha256()
    size = 0
    with source.open("rb") as src, destination.open("wb") as dst:
        while True:
            chunk = src.read(chunk_size)
            if not chunk:
                break
            dst.write(chunk)
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def read_text_bounded(path: Path, max_bytes: int) -> str:
    """Decode at most ``max_bytes`` from a text file."""
    return bounded_sample(path, max_bytes).decode("utf-8", errors="replace")
