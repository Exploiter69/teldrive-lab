#!/usr/bin/env python3
"""Discover an existing TelDrive corpus into the Lab catalog, read-only."""

from __future__ import annotations

import argparse
import json

from teldrive_lab.catalog import open_default_catalog
from teldrive_lab.corpus import CorpusLimits, configured_teldrive_remote, discover_teldrive


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only TelDrive corpus discovery")
    parser.add_argument("--remote", default=configured_teldrive_remote(), help="existing rclone remote, e.g. teldrive:")
    parser.add_argument("--root", default="", help="optional remote subdirectory")
    parser.add_argument("--max-entries", type=int, default=100_000)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--rclone", default="rclone")
    args = parser.parse_args()
    if not args.remote:
        parser.error("--remote is required unless TELDRIVE_LAB_TELDRIVE_RCLONE_REMOTE is set")

    result = discover_teldrive(
        open_default_catalog(),
        remote=args.remote,
        root=args.root,
        executable=args.rclone,
        limits=CorpusLimits(max_entries=args.max_entries, timeout_seconds=args.timeout),
    )
    print(json.dumps({
        "remote": result.remote,
        "root": result.root,
        "source_identifier": result.source_identifier,
        "discovered": result.discovered,
        "skipped": result.skipped,
        "bounded": result.bounded,
        "stale_paths": list(result.stale_paths),
        "observed_at": result.observed_at,
        "mutation": "NONE",
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
