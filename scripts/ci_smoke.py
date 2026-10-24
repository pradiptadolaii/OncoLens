"""Import real inference code and check app startup wiring without private weights."""
import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'app'))
import oncolens_inference
assert oncolens_inference.CLASS_NAMES==['glioma','meningioma','notumor','pituitary']
spec=importlib.util.spec_from_file_location('oncolens_ci',ROOT/'app.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
with patch.dict(os.environ,{'ONCOLENS_USERNAME':'ci-user','ONCOLENS_PASSWORD':'synthetic-ci-password-123456'}),patch.object(module,'prepare_model',return_value=module.MODEL_PATH),patch.object(module,'OncoLensPredictor') as predictor:
    with TestClient(module.app) as client:
        assert client.get('/api/health').status_code==200
        assert client.get('/').status_code==401
        assert client.get('/',auth=('ci-user','synthetic-ci-password-123456')).status_code==200
    predictor.assert_called_once_with(checkpoint_path=module.MODEL_PATH,device='cpu')
print('PASS real dependency imports and authenticated app startup wiring; artifact and predictor construction mocked.')
