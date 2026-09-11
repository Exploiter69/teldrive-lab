from pathlib import Path

from teldrive_lab.advanced import WorkerNode, ai_workflow_plan, dispatch_plan, worker_registry
from teldrive_lab.extended import experimental_registry, validate_extended_safety


def test_stage8_registry_covers_implemented_experiments():
    names = {item.name for item in experimental_registry()}
    assert {
        "content-addressable-index",
        "tiering-simulator",
        "snapshot-compression-benchmark",
        "distributed-worker-protocol",
        "local-ai-orchestration",
    } <= names
    assert all(not item.production_mutation for item in experimental_registry())


def test_stage8_safety_contract_is_non_mutating():
    safety = validate_extended_safety()
    assert safety["production_write"] is False
    assert safety["production_delete"] is False
    assert safety["automatic_eviction"] is False
    assert safety["ai_authority"] is False


def test_untrusted_remote_worker_cannot_mutate_production():
    node = WorkerNode("remote", "ssh://example.invalid", ("transfer",), trusted=False)
    registry = worker_registry([node])
    assert registry["dispatch_policy"] == "explicitly_trusted_only"
    assert dispatch_plan(node, {"production_mutation": True})["allowed"] is False


def test_stage8_ai_plan_keeps_policy_authority():
    result = ai_workflow_plan([{"id": "x", "kind": "advisory"}])
    assert result["authority"] == "policy"
    assert result["ai_authoritative"] is False
    assert result["steps"][0]["requires_policy"] is True
    assert result["steps"][0]["requires_authorization"] is True
    assert result["steps"][0]["requires_verification"] is True
