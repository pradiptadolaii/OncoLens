import importlib.util
import io
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv('ONCOLENS_USERNAME','researcher')
    monkeypatch.setenv('ONCOLENS_PASSWORD','synthetic-test-password-12345')
    spec=importlib.util.spec_from_file_location('oncolens_test_api',ROOT/'app.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with patch.object(module,'prepare_model',return_value=module.MODEL_PATH), patch.object(module,'OncoLensPredictor') as constructor:
        constructor.return_value.predict.return_value={'predicted_class':'glioma','scores':{'glioma':0.25,'meningioma':0.25,'notumor':0.25,'pituitary':0.25},'model':'ResNet18','research_only':True,'medical_diagnosis':False}
        with TestClient(module.app) as client:
            yield client,module,constructor

def png(size=(224,224)):
    output=io.BytesIO();Image.new('RGB',size,'gray').save(output,format='PNG');return output.getvalue()

AUTH=('researcher','synthetic-test-password-12345')

def test_auth_health_and_headers(api):
    client,module,ctor=api
    assert client.get('/api/health').status_code==200
    assert client.get('/').status_code==401
    assert client.get('/',auth=('bad','bad')).status_code==401
    response=client.get('/',auth=AUTH)
    assert response.status_code==200
    assert response.headers['cache-control']=='no-store'
    assert response.headers['x-frame-options']=='DENY'
    assert 'Research prototype' in response.text
    assert client.get('/openapi.json',auth=AUTH).status_code==404
    ctor.assert_called_once_with(checkpoint_path=module.MODEL_PATH,device='cpu')

def test_memory_only_valid_upload(api):
    client,_,ctor=api
    with patch('tempfile.TemporaryFile',side_effect=AssertionError('No disk spooling allowed')):
        response=client.post('/api/predict',auth=AUTH,files={'file':('synthetic.png',png(),'image/png')})
    assert response.status_code==200
    assert set(response.json()['scores'])=={'glioma','meningioma','notumor','pituitary'}
    ctor.return_value.predict.assert_called_once()

@pytest.mark.parametrize('name,data',[('bad.txt',b'x'),('bad.png',b'not image'),('empty.png',b'')])
def test_invalid_images(api,name,data):
    client,_,ctor=api
    assert client.post('/api/predict',auth=AUTH,files={'file':(name,data,'image/png')}).status_code==400
    ctor.return_value.predict.assert_not_called()

def test_oversize_request(api):
    client,_,ctor=api
    assert client.post('/api/predict',auth=AUTH,files={'file':('large.png',b'x'*(10*1024*1024+1),'image/png')}).status_code==413
    ctor.return_value.predict.assert_not_called()

def test_chunked_request_cap(api):
    client,_,_=api
    def chunks():
        for _ in range(12):yield b'x'*(1024*1024)
    response=client.post('/api/predict',auth=AUTH,content=chunks(),headers={'Content-Type':'multipart/form-data; boundary=research'})
    assert response.status_code==413

def test_dimensions_and_actual_format(api):
    client,_,ctor=api
    assert client.post('/api/predict',auth=AUTH,files={'file':('large.png',png((2001,2000)),'image/png')}).status_code==400
    data=io.BytesIO();Image.new('RGB',(20,20),'gray').save(data,format='GIF')
    assert client.post('/api/predict',auth=AUTH,files={'file':('disguised.png',data.getvalue(),'image/png')}).status_code==400
    ctor.return_value.predict.assert_not_called()

def test_origin_and_multipart(api):
    client,_,_=api
    assert client.post('/api/predict',auth=AUTH,files={'file':('image.png',png(),'image/png')},headers={'Origin':'https://other.example'}).status_code==403
    assert client.post('/api/predict',auth=AUTH,files=[('file',('a.png',png())),('file',('b.png',png()))]).status_code==400
    assert client.post('/api/predict',auth=AUTH,content=b'incomplete',headers={'Content-Type':'multipart/form-data; boundary=test'}).status_code==400

def test_rate_limit(api):
    client,_,_=api
    for _ in range(12): assert client.post('/api/predict',auth=AUTH,files={'file':('a.png',png())}).status_code==200
    assert client.post('/api/predict',auth=AUTH,files={'file':('a.png',png())}).status_code==429

def test_model_integrity_refusal(tmp_path):
    from model_artifact import verify_model
    bad=tmp_path/'bad.pth';bad.write_bytes(b'not a checkpoint')
    with pytest.raises(RuntimeError,match='size mismatch'):verify_model(bad)

def test_checksum_mismatch(tmp_path):
    from model_artifact import verify_model, EXPECTED_SIZE
    bad=tmp_path/'wrong.pth'
    with bad.open('wb') as stream:stream.truncate(EXPECTED_SIZE)
    with pytest.raises(RuntimeError,match='SHA-256 mismatch'):verify_model(bad)

def test_missing_auth_refuses_start(monkeypatch):
    monkeypatch.delenv('ONCOLENS_USERNAME',raising=False)
    monkeypatch.delenv('ONCOLENS_PASSWORD',raising=False)
    spec=importlib.util.spec_from_file_location('noauth',ROOT/'app.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with pytest.raises(RuntimeError,match='password'):
        with TestClient(module.app):pass

def test_concurrency_bound(api):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    client,_,ctor=api
    entered=threading.Event();release=threading.Event()
    result=ctor.return_value.predict.return_value
    def slow(image):
        entered.set();assert release.wait(10);return result
    ctor.return_value.predict.side_effect=slow
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(lambda:client.post('/api/predict',auth=AUTH,files={'file':('image.png',png())}))
        try:
            assert entered.wait(10)
            assert client.get('/api/health').status_code==200
            assert client.post('/api/predict',auth=AUTH,files={'file':('image.png',png())}).status_code==503
        finally:release.set()
        assert future.result().status_code==200

def test_private_parts_reassemble_and_verify(tmp_path,monkeypatch):
    import hashlib
    import model_artifact
    content=b'synthetic-transfer-test-bytes'
    monkeypatch.setattr(model_artifact,'EXPECTED_SIZE',len(content))
    monkeypatch.setattr(model_artifact,'EXPECTED_SHA256',hashlib.sha256(content).hexdigest())
    target=tmp_path/'model.pth'
    target.with_name('model.pth.part01').write_bytes(content[:12])
    target.with_name('model.pth.part02').write_bytes(content[12:])
    assert model_artifact.prepare_model(target).read_bytes()==content
    target.unlink()
    target.with_name('model.pth.part02').write_bytes(b'corrupted')
    with pytest.raises(RuntimeError):model_artifact.prepare_model(target)
    assert not target.exists()
    assert not target.with_suffix('.download').exists()
