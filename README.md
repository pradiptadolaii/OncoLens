# OncoLens

**Brain MRI Research Classification Dashboard**

OncoLens is a Biomedical Engineering project by **Pradipta Dolai** ([pradiptadolaii](https://github.com/pradiptadolaii)). It demonstrates a browser dashboard integrated with a FastAPI backend and a four-output PyTorch ResNet18 classifier.

> **Research and education only. This is an experimental prototype, not a clinically validated medical diagnostic system. Do not use it for diagnosis, treatment, or patient care.**

## Objectives and features

- Demonstrate image upload, preprocessing, inference, and visualization in a local research application.
- Classify authorized, de-identified 2D research images into `glioma`, `meningioma`, `notumor`, and `pituitary`.
- Display the selected class and four uncalibrated softmax scores.
- Analyze up to 20 images sequentially through the integrated dashboard panel.
- Explore a separate synthetic-phantom pipeline with segmentation, radiomics, and logistic classification.
- Validate upload formats, file size (10 MB), and image dimensions (25 million pixels) in the API.

## Two distinct research modes

**Analyze MRI Images / Run ResNet18** calls the experimental FastAPI classifier. **Run pipeline** uses synthetic phantoms and a separate JavaScript logistic model. Its cross-validation, segmentation, quantization, and latency figures are demonstration results, not evidence of ResNet18 performance or patient-level accuracy.

## Technology and architecture

Python, FastAPI, Uvicorn, PyTorch, torchvision, NumPy, Pillow, and HTML/CSS/JavaScript.

The inference module constructs `torchvision.models.resnet18(weights=None)` and replaces its final fully connected layer with four outputs. ResNet18 uses residual connections across convolutional blocks, followed by average pooling and the classifier. Parameters come from the research checkpoint; no pretrained weights are downloaded at runtime.

Original preprocessing is preserved: RGB conversion, black padding/resizing to 224 x 224, tensor conversion, and normalization with means `[0.485, 0.456, 0.406]` and standard deviations `[0.229, 0.224, 0.225]`. Evaluation-mode inference is followed by softmax and argmax. The FastAPI application uses CPU inference.

## Installation and execution

Use Python 3.11 (the CI target):

```bash
git clone https://github.com/pradiptadolaii/OncoLens.git
cd OncoLens
python -m venv .venv
```

Activate using `.venv\Scripts\activate` on Windows or `source .venv/bin/activate` on macOS/Linux, then:

```bash
python -m pip install -r requirements.txt
```

**Supply the authorized checkpoint before starting the server.** It is excluded pending confirmation of redistribution rights. See [model setup](models/README.md) for its required name, location, and hash. No public model-download URL is currently available; request authorized access from the author or use the original project archive. A source-only clone cannot start the unchanged backend without this file.

```bash
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Open [the local dashboard](http://127.0.0.1:8000). See [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md).

## FastAPI integration

| Endpoint | Purpose |
| --- | --- |
| `GET /` | Serve the integrated dashboard |
| `GET /api/health` | Return application metadata and research-only flags |
| `POST /api/predict` | Accept multipart field `file`; return `predicted_class`, `scores`, model name, and research-only flags |

The API accepts PNG, JPG/JPEG, BMP, and WEBP. The older Run ResNet18 control accepts PNG/JPEG; the integrated multi-image panel exposes all API formats. DICOM and NIfTI are not supported. Health metadata is not a model-performance assessment.

## Repository structure

```text
OncoLens/
|-- app.py
|-- app/
|   |-- oncolens_dashboard_integrated.html
|   `-- oncolens_inference.py
|-- models/README.md
|-- scripts/ci_smoke.py
|-- .github/workflows/ci.yml
|-- .gitignore
|-- requirements.txt
|-- README.md
|-- INSTALLATION_GUIDE.md
`-- RESEARCH_DISCLAIMER.md
```

The checkpoint belongs at `models/resnet18_audited_experiment_best.pth` locally. No dataset, patient image, or checkpoint is distributed here. No dashboard screenshots were supplied in the original archive.

## Verification

GitHub Actions installs dependencies, runs `pip check`, compiles Python source, imports the real inference module, and imports the application with only predictor construction mocked. This checks application wiring without weights or patient data. It does not validate checkpoint loading, predictions, or diagnostic performance. Direct dependencies are pinned to locally tested Python 3.11 versions with CPU PyTorch. See [Render preparation](RENDER_DEPLOYMENT.md) for deployment blockers and public-access safeguards.

## Research limitations

- Training-time class-index mapping has not been independently verified.
- Independent patient-level accuracy and external four-class accuracy have not been established.
- Softmax scores are not calibrated clinical probabilities; `notumor` does not rule out disease.
- Dataset provenance, training protocol, and checkpoint redistribution rights are not established by the archive.
- Synthetic demonstration metrics cannot establish MRI classifier performance.
- Use only appropriately de-identified images with permission. Keep the server on localhost; this prototype has no authentication or production deployment hardening.
- External font stylesheets may require internet access.

See [RESEARCH_DISCLAIMER.md](RESEARCH_DISCLAIMER.md). No model performance metrics or clinical validation claims are made here.

## Author and project context

**Pradipta Dolai** - Biomedical Engineering  - OncoLens research prototype.

Application and prediction logic are preserved from the supplied working project. Publication adds documentation and CI. No software or model redistribution license has been inferred or granted by publication.
