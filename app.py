import io
import os
import sys
import warnings
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from model_artifact import prepare_model
from security import ResearchSecurity
from uploads import read_image_upload

ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT / 'app'
MODEL_PATH = ROOT / 'models' / 'resnet18_audited_experiment_best.pth'
sys.path.insert(0, str(APP_DIR))
from oncolens_inference import OncoLensPredictor

predictor = None
MAX_IMAGE_PIXELS = int(os.environ.get('ONCOLENS_MAX_IMAGE_PIXELS','4000000'))
if not 1 <= MAX_IMAGE_PIXELS <= 25_000_000:
    raise RuntimeError('Image limit must be between 1 and 25000000 pixels.')

@asynccontextmanager
async def lifespan(app):
    global predictor
    if not os.environ.get('ONCOLENS_USERNAME') or len(os.environ.get('ONCOLENS_PASSWORD','')) < 20:
        raise RuntimeError('Set research username and a password of at least 20 characters in secrets.')
    checkpoint = prepare_model(MODEL_PATH)
    predictor = OncoLensPredictor(checkpoint_path=checkpoint, device='cpu')
    try:
        yield
    finally:
        predictor = None

app = FastAPI(title='OncoLens Research API', version='1.1', lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(ResearchSecurity)

@app.get('/')
def dashboard():
    return FileResponse(APP_DIR/'oncolens_dashboard_integrated.html', media_type='text/html')

@app.get('/api/health')
def health():
    if predictor is None:
        raise HTTPException(503, 'Model is not ready.')
    return {'status':'ok','model':'ResNet18','research_only':True,'medical_diagnosis':False}

def decode_and_predict(filename,content):
    if Path(filename).suffix.lower() not in {'.png','.jpg','.jpeg','.bmp','.webp'}:
        raise HTTPException(400,'Supported image types: PNG, JPG, JPEG, BMP, WEBP')
    if not content:
        raise HTTPException(400,'Empty upload.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as source:
                if source.format not in {'PNG','JPEG','BMP','WEBP'}:
                    raise ValueError('Unsupported decoded format.')
                if source.width*source.height>MAX_IMAGE_PIXELS:
                    raise ValueError('Image exceeds dimension limit.')
                source.verify()
            with Image.open(io.BytesIO(content)) as source:
                image = source.convert('RGB').copy()
    except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError,Image.DecompressionBombWarning):
        raise HTTPException(400,'Invalid image or image dimensions exceed the research limit.') from None
    try:
        return predictor.predict(image)
    except Exception:
        raise HTTPException(500,'Prediction failed.') from None

@app.post('/api/predict')
async def predict_image(request: Request):
    filename,content = await read_image_upload(request)
    return await run_in_threadpool(decode_and_predict,filename,content)
