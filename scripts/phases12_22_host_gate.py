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
from teldrive_lab.advanced import (
    CASStore, StorageHeat, access_frequency, ai_workflow_plan, category_analysis,
    content_index, create_snapshot, dedup_plan, extended_safety, eviction_plan,
    export_metadata, growth_forecast, local_embedding, media_records,
    project_contracts, resource_budget, search_content, storage_heatmap,
    storage_tier, transfer_cost_estimate, verify_snapshot,
)


def main() -> int:
    safety = validate_extended_safety()
    assert safety["production_write"] is False
    assert safety["production_delete"] is False
    assert safety["automatic_eviction"] is False
    assert safety["telldrive_db_write"] is False
    assert safety["ai_authority"] is False
    assert safety["all_mutations_require_explicit_authorization"] is True
    advanced = extended_safety()
    for key in ("production_write","production_delete","automatic_eviction","teldrive_db_write","ai_authority","ui_mutation","remote_worker_mutation"):
        assert advanced[key] is False
    assert advanced["all_mutations_require_explicit_authorization"] is True
    with tempfile.TemporaryDirectory(prefix="teldrive-lab-phases12-22-") as raw:
        root=Path(raw); (root/'cache').mkdir(); (root/'fixture.txt').write_text('safe fixture')
        obs=observe_storage(root); assert len(obs)==1 and obs[0].path=='fixture.txt'
        manifest=root/'snapshot.json'; create_snapshot_manifest(root,manifest)
        assert verify_snapshot_manifest(manifest,root)['verified']
        payload=control_center_payload(root); assert payload['ui_mutation_policy']=='none'
        assert integration_contracts() and not local_ai_advisory('secret token').authoritative
        (root/'hot.txt').write_text('hot content'); access_db=root/'access.db'
        from teldrive_lab.advanced import record_access
        for _ in range(10): record_access(access_db,str(root/'hot.txt'))
        heat=storage_heatmap(root,access_db); assert any(h.tier=='hot' for h in heat)
        assert eviction_plan(heat,1)['action']=='PLAN_ONLY'; assert resource_budget(512,256,4,8)==2
        out=root/'metadata.json'; export_metadata([{'name':'fixture.txt'}],out); assert out.exists()
        assert media_records(root)==[]; assert storage_tier(10,999999)=='hot'
        idx=content_index([root/'fixture.txt']); assert search_content(idx,'safe')
        assert len(local_embedding('safe'))==256
        assert growth_forecast([(0,100),(86400,200)])['bytes_per_day']==100
        assert category_analysis(root.iterdir())
        assert transfer_cost_estimate(1024)['currency']=='NONE'
        # A snapshot manifest must live outside the tree it describes. Placing
        # it inside root would make the newly-created manifest an extra file
        # during verification and create a self-referential snapshot boundary.
        snap=Path(raw).parent/'advanced-snapshot.json'
        snap_data=create_snapshot(root,snap); assert verify_snapshot(snap,root)['verified']
        assert project_contracts() and ai_workflow_plan([{'id':'gate'}])['ai_authoritative'] is False
        cas=CASStore(root/'cas'); digest=cas.put(root/'fixture.txt'); assert cas.has(digest)
        assert dedup_plan([root/'fixture.txt'])==[]
    print('PHASES 12-22 HOST GATE: PASS')
    print('roadmap capabilities: PASS')
    print('advanced capabilities: PASS')
    print('production storage mutation: NONE')
    print('AI authority: NONE')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
