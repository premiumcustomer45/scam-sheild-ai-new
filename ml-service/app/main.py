from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import joblib
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.schemas import Prediction, TextInput, UrlInput
from app.services.scoring import predict_combined, predict_text, predict_url

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger("scamshield.ml")
MODEL_DIR = Path(os.environ.get("MODEL_DIR", Path(__file__).resolve().parents[1] / "models"))


def _load_bundle(path: Path, expected_type: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(
            f"Required {expected_type} model artifact is missing at {path}. "
            "Train it with the documented ml-service/training command before starting inference."
        )
    bundle = joblib.load(path)
    if not isinstance(bundle, dict) or "model" not in bundle or "metadata" not in bundle:
        raise RuntimeError(f"Invalid {expected_type} model artifact structure at {path}.")
    metadata = bundle["metadata"]
    if metadata.get("model_type") != expected_type:
        raise RuntimeError(f"Model artifact at {path} does not match {expected_type}.")
    if not metadata.get("model_version"):
        raise RuntimeError(f"Model metadata at {path} is missing model_version.")
    return bundle


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.url_bundle = _load_bundle(MODEL_DIR / "url_model.joblib", "url")
        app.state.text_bundle = _load_bundle(MODEL_DIR / "text_model.joblib", "text")
    except Exception:
        logger.exception("ML service model initialization failed")
        raise
    logger.info(
        "ML service ready",
        extra={
            "url_model": app.state.url_bundle["metadata"]["model_version"],
            "text_model": app.state.text_bundle["metadata"]["model_version"],
        },
    )
    yield


app = FastAPI(
    title="ScamShield AI ML Service",
    version="1.0.0",
    description="Local model inference. Submitted URLs are parsed only and are never fetched.",
    lifespan=lifespan,
)


@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > 65536:
        return JSONResponse(status_code=413, content={"detail": "Request body is too large."})
    return await call_next(request)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def readiness(request: Request):
    if not hasattr(request.app.state, "url_bundle") or not hasattr(
        request.app.state, "text_bundle"
    ):
        raise HTTPException(status_code=503, detail="Models are not loaded.")
    return {"status": "ready"}


@app.post("/predict/url", response_model=Prediction)
async def url_prediction(payload: UrlInput, request: Request):
    try:
        return predict_url(payload.url, request.app.state.url_bundle)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("URL inference failed")
        raise HTTPException(status_code=500, detail="URL assessment failed.") from exc


@app.post("/predict/text", response_model=Prediction)
async def text_prediction(payload: TextInput, request: Request):
    try:
        return predict_text(payload.text, request.app.state.text_bundle)
    except Exception as exc:
        logger.exception("Text inference failed")
        raise HTTPException(status_code=500, detail="Message assessment failed.") from exc


@app.post("/predict/combined", response_model=Prediction)
async def combined_prediction(payload: TextInput, request: Request):
    try:
        return predict_combined(
            payload.text,
            request.app.state.text_bundle,
            request.app.state.url_bundle,
        )
    except Exception as exc:
        logger.exception("Combined inference failed")
        raise HTTPException(status_code=500, detail="Combined assessment failed.") from exc
