from teldrive_lab.advanced import *


def test_p12_access_heat_prefetch_eviction_and_budget(tmp_path):
    p=tmp_path/'hot.txt'; p.write_text('x'*10); db=tmp_path/'access.db'
    for _ in range(10): record_access(db,str(p))
    heat=storage_heatmap(tmp_path,db); hot=next(x for x in heat if x.path.endswith('hot.txt'))
    assert hot.tier=='hot'; assert prefetch_suggestions(heat)
    assert eviction_plan(heat,1)['action']=='PLAN_ONLY'
    assert resource_budget(512,256,4,8)==2


def test_p12_pressure(tmp_path):
    (tmp_path/'a').write_bytes(b'x'*80); assert cache_pressure(tmp_path,100)['pressure']=='high'


def test_p13_export_import_and_view(tmp_path):
    out=tmp_path/'m.json'; export_metadata([{'name':'x'}],out); assert validate_metadata_export(out)['valid']; assert import_metadata(out)==[{'name':'x'}]; assert filesystem_metadata_view(tmp_path)


def test_p14_media_subtitle_probe(tmp_path):
    (tmp_path/'movie.mkv').write_bytes(b'x'); (tmp_path/'movie.en.srt').write_text('1')
    assert media_records(tmp_path)[0]['extension']=='.mkv'; assert subtitle_index(tmp_path); assert media_integrations(); assert thumbnail_capability()


def test_p15_document_ocr_embedding_and_vision(tmp_path):
    p=tmp_path/'note.md'; p.write_text('hello local intelligence'); fp=document_fingerprint(p)
    assert fp['text_available'] and len(fp['sha256'])==64 and len(local_embedding('hello'))==256
    assert isinstance(ocr(p),dict); assert isinstance(image_vision_summary(p),dict)


def test_p15_pdf_capability(tmp_path):
    p=tmp_path/'x.pdf'; p.write_bytes(b'%PDF-1.4\n'); assert 'fields' in pdf_metadata(p)


def test_p16_content_search(tmp_path):
    a=tmp_path/'a.txt'; b=tmp_path/'b.txt'; a.write_text('VAJRA durable engineering'); b.write_text('banana')
    idx=content_index([a,b]); result=search_content(idx,'VAJRA engineering'); assert result and result[0]['path']==str(a)


def test_p17_ai_is_advisory():
    p=ai_proposal('ARCHIVE','because it is cold',.8); assert not p.authoritative and p.requires_policy and p.requires_authorization
    assert natural_language_search('x',{'docs':{},'df':{}})==[]


def test_p18_storage_analytics(tmp_path):
    (tmp_path/'a.txt').write_bytes(b'x'*10); (tmp_path/'b.pdf').write_bytes(b'x'*20)
    analysis=category_analysis(tmp_path.iterdir()); assert analysis['.txt']['bytes']==10
    assert growth_forecast([(0,100),(86400,200)])['bytes_per_day']==100
    assert transfer_cost_estimate(1_000_000)['currency']=='NONE'


def test_p19_incremental_snapshot_restore_retention(tmp_path):
    root=tmp_path/'root'; root.mkdir(); (root/'a').write_text('one'); snap1=tmp_path/'s1.json'; first=create_snapshot(root,snap1)
    (root/'a').write_text('two'); (root/'b').write_text('b'); snap2=tmp_path/'s2.json'; second=create_snapshot(root,snap2,first)
    assert second['incremental']['changed']; assert verify_snapshot(snap2,root)['verified']; assert restore_plan(second,tmp_path/'restore')['requires_authorization']
    assert retention_plan([first,second],1)['expire']


def test_p20_cross_project_contracts():
    cs=project_contracts(); assert {c.name for c in cs}>={'VAJRA','Alok Engineering Lab','local-development','dataset-workflow','experiment-archive'}
    assert validate_project_request(cs[0],cs[0].capabilities[0])['allowed']; assert not validate_project_request(cs[0],cs[0].capabilities[0],production_write=True)['allowed']


def test_p21_cas_dedup_tiering_compression_and_workers(tmp_path):
    a=tmp_path/'a'; b=tmp_path/'b'; a.write_bytes(b'hello'); b.write_bytes(b'hello'); cas=CASStore(tmp_path/'cas'); digest=cas.put(a); assert cas.has(digest)
    plan=dedup_plan([a,b]); assert plan and plan[0]['action']=='REPORT_ONLY'
    heat=[StorageHeat(str(a),5,0,0,'cold',0)]; assert tiering_plan(heat)[0]['action']=='PLAN_ONLY'
    snap=tmp_path/'s.json'; snap.write_text('{}'); compressed_snapshot(snap,tmp_path/'s.json.gz'); assert (tmp_path/'s.json.gz').exists()
    node=WorkerNode('n1','127.0.0.1',('index',),trusted=True); assert dispatch_plan(node,{'production_mutation':False})['allowed']; assert not dispatch_plan(node,{'production_mutation':True})['allowed']
    assert ai_workflow_plan([{'id':'x'}])['ai_authoritative'] is False


def test_p22_control_center_is_read_only():
    payload=control_center_payload(health={'ok':True}); assert payload['authority']=='teldrive'; assert payload['ui_mutation_policy']=='none'; assert '/api/audit' in payload['routes']


def test_global_p12_p22_safety():
    safety=extended_safety(); assert all(not safety[k] for k in ('production_write','production_delete','automatic_eviction','teldrive_db_write','ai_authority','ui_mutation','remote_worker_mutation')); assert safety['all_mutations_require_explicit_authorization']
