"""Consolidated safe host gate for Phases 12-22.

Only exercises Lab-owned temporary state. It never mounts, writes, deletes,
reorganizes, or reconfigures TelDrive production storage.
"""
from __future__ import annotations
import tempfile
from pathlib import Path
from teldrive_lab.extended import (
    control_center_payload, create_snapshot_manifest, integration_contracts,
    local_ai_advisory, observe_storage, validate_extended_safety,
    verify_snapshot_manifest,
)


def main() -> int:
    safety = validate_extended_safety()
    assert safety["production_write"] is False
    assert safety["production_delete"] is False
    assert safety["automatic_eviction"] is False
    assert safety["teldrive_db_write"] is False
    assert safety["ai_authority"] is False
    assert safety["all_mutations_require_explicit_authorization"] is True
    with tempfile.TemporaryDirectory(prefix="teldrive-lab-phases12-22-") as raw:
        root=Path(raw); (root/'cache').mkdir(); (root/'fixture.txt').write_text('safe fixture')
        obs=observe_storage(root); assert len(obs)==1 and obs[0].path=='fixture.txt'
        manifest=root/'snapshot.json'; create_snapshot_manifest(root,manifest)
        assert verify_snapshot_manifest(manifest,root)['verified']
        payload=control_center_payload(root); assert payload['ui_mutation_policy']=='none'
        assert integration_contracts() and not local_ai_advisory('secret token').authoritative
    print('PHASES 12-22 HOST GATE: PASS')
    print('advanced capabilities: PASS')
    print('production storage mutation: NONE')
    print('AI authority: NONE')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
