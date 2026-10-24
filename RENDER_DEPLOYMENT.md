# Render deployment

This branch adds cloud transport controls and keeps the inference module and dashboard unchanged.

## Proposed service

Name: oncolens-research. Runtime: Python 3.11.17. One worker.
Build: pip install -r requirements.txt
Start: uvicorn app:app --host 0.0.0.0 --port $PORT
Health: /api/health
Plan proposal: 1c-2g (2 GB, 1 CPU), currently advertised at USD 25/month compute. No paid creation is authorized until the owner explicitly approves. Auto-deploy is off. Use the Hobby workspace unless the owner approves a workspace upgrade. Usage overages, tax, and optional services are not authorized.

## Private model delivery

The owner confirmed hosting and inference rights on 24 October 2026 and requested private weights. This confirmation does not authorize public redistribution. Keep the original checkpoint and all parts out of the public OncoLens repository.

Recommended source is a PRIVATE deployment mirror named OncoLens-Render-Private. Render's GitHub integration clones it under its normal private-repository access controls. Place two binary parts in models, named resnet18_audited_experiment_best.pth.part01 and resnet18_audited_experiment_best.pth.part02. Splitting is only a transfer mechanism for GitHub's browser upload limit. Startup reconstructs the exact original bytes and verifies the full size and SHA-256 before loading. No model transformation, compression, or retraining occurs.

Expected size: 44,792,971 bytes. SHA-256: 4ba78eaa0302a8cf35f846316888b720fbc4ce7c5ed86946b1d8fb657e0dd3a4.

Alternative: provide ONCOLENS_MODEL_PATH for an authorized mounted artifact, or ONCOLENS_MODEL_URL with optional ONCOLENS_MODEL_TOKEN in Render secrets. Downloads require HTTPS, enforce expected size, verify SHA-256, and use atomic placement. Bearer authorization is not forwarded to a different redirect host. Download URLs and tokens are never printed. Missing or mismatched bytes fail startup.

Never expose a checkpoint download route. The service exposes only the HTML and research API; the model is not a static asset.

## Secrets and access

Set ONCOLENS_USERNAME and ONCOLENS_PASSWORD in the Render environment. Passwords must contain at least 20 characters. Keep values out of Git, chat, screenshots, and logs. HTTP Basic authentication over Render HTTPS protects the dashboard and prediction route. The health endpoint stays public and returns only research metadata. API docs/schema endpoints are disabled.

For local use set the same variables in your shell before starting the service. Browser same-origin fetch automatically uses the established Basic login. No shared secret is embedded in HTML.

## Upload and availability controls

- No UploadFile spooling: a bounded memory-only parser accepts exactly one multipart file.
- Maximum image bytes 10 MiB; total multipart body cap adds 64 KiB overhead. Content-Length and streamed bodies are checked. Multipart headers and boundary length are bounded.
- A 20-second upload deadline, actual decoded-format validation, decompression-bomb rejection, and a 4-million-pixel cloud cap reduce resource exposure. The original ceiling can be configured up to 25 million, but increasing it requires memory reassessment.
- One active upload/decode/prediction at a time. Excess work receives 503, authenticated predictions are limited to 12/minute globally per worker, and non-health requests to 120/minute globally.
- Health remains responsive while synchronous image/model work runs in the bounded worker thread.
- Origin, if provided, must match Host. No permissive CORS configuration is added. Responses use no-store, anti-framing, nosniff, and no-referrer headers. Uvicorn access logging is disabled by environment setting.
- No uploaded content or filename logging or application disk storage is implemented. Provider edge/operating-system behavior is outside this guarantee. Use only synthetic or authorized de-identified research images.
- External font services remain in the unchanged dashboard. Shared Basic credentials and process-local limits are suitable only for a limited research demonstration, not a clinical service or distributed security perimeter.

## Verification and remaining cloud gates

Python 3.11.17 CPU dependency installation passed locally. Fifteen security/application tests passed, with predictor construction mocked for resource-independent tests. A separate real Uvicorn process loaded the actual checkpoint, returned dashboard and health 200, returned finite four-class scores for artificial 224x224 and 2000x2000 PNGs, and rejected invalid images (400), oversized files (413), and images beyond the cloud dimension limit (400).

Measured local Windows process-tree peak working set was 453.9 MiB including startup and accepted maximum-size synthetic input. This is not a Linux Render measurement and is too close to a 512 MB limit to establish free-instance reliability. A 2 GB proposal leaves headroom. Verify actual Render memory after deployment.

Cloud build, runtime logs, deployed commit, HTTPS health, authenticated prediction, and actual plan/cost are pending until the private model source and paid-instance approval are complete. Do not report live deployment from local checks.

Research only. No clinical validation, verified patient-level accuracy, or calibrated diagnostic probabilities are claimed.
