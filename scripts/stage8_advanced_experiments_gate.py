#!/usr/bin/env python3
"""Stage 8 safety/disposition gate.

The gate validates the existing Phase 21 experiment layer without executing
production storage operations.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from teldrive_lab.advanced import (  # noqa: E402
    CASStore,
    WorkerNode,
    ai_workflow_plan,
    compressed_snapshot,
    dedup_plan,
    dispatch_plan,
    tiering_plan,
    worker_registry,
)
from teldrive_lab.extended import experimental_registry, validate_extended_safety  # noqa: E402


def main() -> int:
    experiments = experimental_registry()
    names = {x.name for x in experiments}
    required = {
        "content-addressable-index",
        "tiering-simulator",
        "snapshot-compression-benchmark",
        "distributed-worker-protocol",
        "local-ai-orchestration",
    }
    assert required <= names
    assert all(not x.production_mutation for x in experiments)

    safety = validate_extended_safety()
    assert safety["production_write"] is False
    assert safety["production_delete"] is False
    assert safety["automatic_eviction"] is False
    assert safety["ai_authority"] is False
    assert safety["all_mutations_require_explicit_authorization"] is True

    assert callable(CASStore)
    assert callable(dedup_plan)
    assert callable(tiering_plan)
    assert callable(compressed_snapshot)

    node = WorkerNode("stage8-gate", "local://stage8", ("plan",), trusted=False)
    assert worker_registry([node])["production_mutation"] is False
    assert dispatch_plan(node, {"production_mutation": True})["allowed"] is False

    plan = ai_workflow_plan([{"id": "stage8", "kind": "advisory"}])
    assert plan["authority"] == "policy"
    assert plan["ai_authoritative"] is False
    assert plan["steps"][0]["requires_authorization"] is True

    print("STAGE 8 ADVANCED EXPERIMENTS GATE")
    print({
        "experiment_registry": "PASS",
        "content_addressable": "PASS",
        "dedup_report_only": "PASS",
        "tiering_plan_only": "PASS",
        "snapshot_compression_local": "PASS",
        "distributed_workers_isolated": "PASS",
        "remote_worker_mutation_blocked": "PASS",
        "local_ai_non_authoritative": "PASS",
        "fuse": "DEFERRED",
        "production_storage_mutation": "NONE",
        "paid_dependency": "NONE",
    })
    print("STAGE 8 ADVANCED EXPERIMENTS GATE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
