from teldrive_lab.media_intelligence import classify_document, perceptual_fingerprint, vision_model_capability
from teldrive_lab.interop import serve_ipc


def test_document_classification_and_fingerprint(tmp_path):
    p=tmp_path/'notes.md'; p.write_text('hello'); result=classify_document(p)
    assert result['category']=='document/text' and not result['authoritative']
    assert len(perceptual_fingerprint(p))==64
    assert vision_model_capability()['remote'] is False


def test_ipc_server_is_read_only(tmp_path):
    path=tmp_path/'lab.sock'; server=serve_ipc(path,lambda req:{'ok':True,'op':req['op']})
    try:
        assert server.server_address == str(path)
        assert server.provider({'op':'health'})['ok']
    finally:
        server.server_close()
        if path.exists(): path.unlink()
