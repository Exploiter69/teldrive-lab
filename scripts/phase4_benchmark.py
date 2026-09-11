"""Benchmark local transfer limits without touching production storage."""

from __future__ import annotations

import argparse
import tempfile
import time
from pathlib import Path

from teldrive_lab.concurrency import TransferLimiter, TransferLimits
from teldrive_lab.safety import AuthorizationReceipt, Operation
from teldrive_lab.transfer import TransferManager, TransferSpec


def run(size_mib: int, workers: int) -> float:
    with tempfile.TemporaryDirectory(prefix="teldrive-lab-phase4-bench-") as root:
        base = Path(root)
        source = base / "source.bin"
        destination = base / "destination.bin"
        source.write_bytes(b"0" * (size_mib * 1024 * 1024))
        manager = TransferManager(
            limiter=TransferLimiter(
                TransferLimits(max_workers=workers, max_inflight_bytes=max(1, size_mib * 1024 * 1024))
            )
        )
        receipt = AuthorizationReceipt.for_paths(Operation.TRANSFER, source, destination)
        started = time.perf_counter()
        result = manager.transfer(TransferSpec(str(source), str(destination)), authorization=receipt)
        elapsed = time.perf_counter() - started
        if not result.success:
            raise RuntimeError(result.error or "benchmark transfer failed")
        print(f"workers={workers} size_mib={size_mib} seconds={elapsed:.4f} mib_per_sec={size_mib / elapsed:.2f}")
        return elapsed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size-mib", type=int, default=16)
    parser.add_argument("--workers", type=int, nargs="+", default=[1, 2])
    args = parser.parse_args()
    if args.size_mib < 1 or any(worker < 1 for worker in args.workers):
        raise SystemExit("size and workers must be positive")
    for worker in args.workers:
        run(args.size_mib, worker)
    print("PHASE 4 BENCHMARK: PASS — synthetic local workload only")
    print("Use measured results to choose future concurrency; this script changes no production configuration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
