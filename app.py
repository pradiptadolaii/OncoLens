
import io
import sys
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT / "app"
MODEL_PATH = (
    ROOT / "models" /
    "resnet18_audited_experiment_best.pth"
)

sys.path.insert(0, str(APP_DIR))

from oncolens_inference import OncoLensPredictor

app = FastAPI(
    title="OncoLens Research API",
    version="1.0"
)

predictor = OncoLensPredictor(
    checkpoint_path=MODEL_PATH,
    device="cpu"
)

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000

@app.get("/")
def dashboard():
    return FileResponse(
        APP_DIR /
        "oncolens_dashboard_integrated.html",
        media_type="text/html"
    )

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "model": "ResNet18",
        "research_only": True,
        "medical_diagnosis": False
    }

@app.post("/api/predict")
async def predict_image(
    file: UploadFile = File(...)
):
    filename = file.filename or ""

    allowed_extensions = {
        ".png", ".jpg", ".jpeg",
        ".bmp", ".webp"
    }

    suffix = Path(filename).suffix.lower()

    if suffix not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=(
                "Supported image types: "
                "PNG, JPG, JPEG, BMP, WEBP"
            )
        )

    content = await file.read(
        MAX_FILE_BYTES + 1
    )

    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Image exceeds 10 MB limit."
        )

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Empty upload."
        )

    try:
        with Image.open(
            io.BytesIO(content)
        ) as image:
            image.verify()

        with Image.open(
            io.BytesIO(content)
        ) as image:
            if (
                image.width * image.height
                > MAX_IMAGE_PIXELS
            ):
                raise ValueError(
                    "Image dimensions too large."
                )

            image = image.convert("RGB").copy()

    except (
        UnidentifiedImageError,
        OSError,
        ValueError
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid image."
        )

    try:
        result = predictor.predict(image)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Prediction failed."
        )

    return result
