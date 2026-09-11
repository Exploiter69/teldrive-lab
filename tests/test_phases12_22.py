from pathlib import Path

from teldrive_lab.extended import (
    Advisory, advisory_contract, cache_eviction_plan, cache_pressure,
    concurrency_budget, content_search, control_center_payload,
    create_snapshot_manifest, document_fingerprint, experimental_registry,
    growth_forecast, integration_contracts, local_ai_advisory, media_library_manifest,
    observe_storage, scan_media, storage_economics, validate_catalog_export,
    validate_extended_safety, verify_snapshot_manifest,
)


def test_phase12_storage_and_resource_intelligence(tmp_path):
    p=tmp_path/'hot.txt'; p.write_text('x'); obs=observe_storage(tmp_path)
    assert obs and obs[0].tier == 'hot'
    assert cache_pressure(tmp_path, 100)['used_bytes'] >= 0
    assert concurrency_budget(ram_available_mb=512, per_worker_mb=256, max_workers=8) == 2
    assert cache_eviction_plan(obs, target_bytes=1)['action'] == 'PLAN_ONLY'


def test_phase13_metadata_export_is_read_only(tmp_path):
    db=tmp_path/'catalog.db'; import sqlite3
    c=sqlite3.connect(db); c.execute('create table files(id integer, name text)'); c.execute("insert into files values(1,'x')"); c.commit(); c.close()
    out=tmp_path/'export.json'; from teldrive_lab.extended import export_catalog_metadata
    export_catalog_metadata(db,out); result=validate_catalog_export(out)
    assert result['valid'] and result['tables']==['files']


def test_phase14_media_sidecar_manifest(tmp_path):
    (tmp_path/'movie.mkv').write_bytes(b'video'); records=scan_media(tmp_path)
    assert records[0].extension == '.mkv'; assert media_library_manifest(records)['sidecar_only']


def test_phase15_document_fingerprint(tmp_path):
    p=tmp_path/'note.md'; p.write_text('# Hello\nworld')
    fp=document_fingerprint(p); assert fp['text_available'] and len(fp['sha256'])==64


def test_phase16_content_search(tmp_path):
    p=tmp_path/'a.txt'; p.write_text('VAJRA safe search')
    assert content_search([p],'vajra')[0]['matches']==1


def test_phase17_ai_is_advisory():
    a=local_ai_advisory('please inspect this secret token'); assert isinstance(a,Advisory) and not a.authoritative
    assert advisory_contract(a)['policy_required']


def test_phase18_forecast_and_economics(tmp_path):
    (tmp_path/'a').write_bytes(b'x'*10); obs=observe_storage(tmp_path)
    econ=storage_economics(obs, duplicate_bytes=5); assert econ['total_bytes']>=10 and econ['reclaimable_estimate']==5
    assert growth_forecast([(0,100),(86400,200)])['bytes_per_day']==100.0


def test_phase19_snapshot_roundtrip(tmp_path):
    (tmp_path/'a.txt').write_text('hello'); manifest=tmp_path/'snapshot.json'; create_snapshot_manifest(tmp_path,manifest)
    result=verify_snapshot_manifest(manifest,tmp_path); assert result['verified']
    (tmp_path/'a.txt').write_text('changed'); assert not verify_snapshot_manifest(manifest,tmp_path)['verified']


def test_phase20_contracts_are_read_only():
    contracts=integration_contracts(); assert contracts and all(not c.production_write for c in contracts)


def test_phase21_experiments_are_isolated():
    assert experimental_registry() and all(not x.production_mutation for x in experimental_registry())


def test_phase22_control_center_is_not_authority(tmp_path):
    payload=control_center_payload(tmp_path); assert payload['authority']=='teldrive'; assert payload['ui_mutation_policy']=='none'


def test_global_safety_invariants():
    assert validate_extended_safety()=={'production_write':False,'production_delete':False,'automatic_eviction':False,'telldrive_db_write':False,'ai_authority':False,'all_mutations_require_explicit_authorization':True}
