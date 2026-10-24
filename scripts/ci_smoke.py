"""Check real imports and API wiring without private model weights."""
import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
import oncolens_inference

assert oncolens_inference.CLASS_NAMES == ["glioma", "meningioma", "notumor", "pituitary"]
spec = importlib.util.spec_from_file_location("oncolens_api_smoke", ROOT / "app.py")
module = importlib.util.module_from_spec(spec)
with patch.object(oncolens_inference, "OncoLensPredictor") as predictor:
    spec.loader.exec_module(module)
    predictor.assert_called_once_with(
        checkpoint_path=ROOT / "models" / "resnet18_audited_experiment_best.pth", device="cpu"
    )
routes = {(r.path, method) for r in module.app.routes for method in r.methods}
assert {("/", "GET"), ("/api/health", "GET"), ("/api/predict", "POST")} <= routes
assert module.health()["research_only"] is True
assert module.health()["medical_diagnosis"] is False
assert Path(module.dashboard().path).is_file()
print("PASS: real inference imports and FastAPI wiring; predictor construction mocked; no inference tested.")
