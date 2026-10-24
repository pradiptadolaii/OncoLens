# Installation guide

## Prerequisites

Use Python 3.11, sufficient disk space for PyTorch, internet for initial installation, and authorized access to the original checkpoint. Direct dependencies are pinned to locally tested versions with CPU PyTorch.

## Setup

```bash
git clone https://github.com/pradiptadolaii/OncoLens.git
cd OncoLens
python -m venv .venv
```

Windows PowerShell activation:

```powershell
.venv\Scripts\Activate.ps1
```

macOS/Linux activation:

```bash
source .venv/bin/activate
```

Install:

```bash
python -m pip install -r requirements.txt
python -m pip check
```

## Checkpoint (required)

Follow [models/README.md](models/README.md). Copy the authorized original checkpoint into `models/resnet18_audited_experiment_best.pth` and verify its SHA-256. This repository has no weights or approved public model download URL. Do not publish weights until redistribution rights are established.

## Launch

Run from the directory containing `app.py`:

```bash
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Select authorized, de-identified 2D research images in **Live MRI Research Analysis**, then click **Analyze MRI Images**. Up to 20 files are submitted sequentially. Supported formats: PNG, JPG/JPEG, BMP, WEBP. Maximum size: 10 MB per file. DICOM/NIfTI are unsupported.

`GET /api/health` returns application metadata. `POST /api/predict` accepts multipart field `file`. The synthetic-phantom pipeline is a separate demonstration.

## Checks without weights

```bash
python -m compileall -q app.py app scripts
python scripts/ci_smoke.py
```

The smoke check mocks predictor construction only during the check. It verifies dependency imports and route registration, not model predictions. Normal startup still requires the checkpoint.

## Troubleshooting

- Missing model: verify the exact filename and relative location.
- State-dict mismatch: use the authorized original four-output checkpoint.
- Dependency import error: use a fresh environment and compatible torch/torchvision versions; inspect CI for current installation results.
- Rejected upload: check format, validity, size, and dimensions.
- Unavailable fonts: external font services may be unreachable; local fallback fonts are provided.

Keep the server on localhost. This prototype has no authentication and is not intended as a public inference service. Read [RESEARCH_DISCLAIMER.md](RESEARCH_DISCLAIMER.md).

Deployment branch local startup additionally requires ONCOLENS_USERNAME and ONCOLENS_PASSWORD (20 characters minimum) in the shell environment. See RENDER_DEPLOYMENT.md. The exact original model and preprocessing remain required. The cloud image-dimension limit is 4 million pixels.
