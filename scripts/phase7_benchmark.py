"""Optional Phase 7 hash benchmark; never installs dependencies or changes policy."""

from __future__ import annotations

import argparse
import json

from teldrive_lab.integrity import benchmark_hash_algorithms


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--iterations", type=int, default=1)
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be >= 1")
    print(json.dumps(benchmark_hash_algorithms(args.path, iterations=args.iterations), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
