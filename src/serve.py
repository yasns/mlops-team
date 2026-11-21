"""Inference API: loads models:/banking77@champion from the cluster MLflow at start-up.

MLFLOW_TRACKING_URI=http://127.0.0.1:5005 uvicorn serve:app --app-dir src --port 8000
"""

import os
import time
from contextlib import asynccontextmanager

import mlflow
import pandas as pd
from fastapi import FastAPI, HTTPException, Request, Response
from mlflow import MlflowClient
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field

MODEL_NAME = os.environ.get("MODEL_NAME", "banking77")
MODEL_ALIAS = os.environ.get("MODEL_ALIAS", "champion")

state = {"model": None, "version": None, "run_id": None, "error": None}

REQUESTS = Counter(
    "banking77_api_requests_total", "HTTP requests", ["method", "path", "status"]
)
LATENCY = Histogram(
    "banking77_api_request_duration_seconds",
    "Request latency in seconds",
    ["path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)
PREDICTIONS = Counter(
    "banking77_predictions_total", "Predictions by intent", ["intent", "model_version"]
)
CONFIDENCE = Histogram(
    "banking77_prediction_confidence",
    "Top-class probability of each prediction",
    buckets=(0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99),
)


def load_champion() -> None:
    mv = MlflowClient().get_model_version_by_alias(MODEL_NAME, MODEL_ALIAS)
    state["model"] = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}/{mv.version}")
    state["version"] = int(mv.version)
    state["run_id"] = mv.run_id


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        load_champion()
    except Exception as exc:  # noqa: BLE001 - any failure -> /health 503, pod stays unready
        state["error"] = str(exc)
    yield


app = FastAPI(title="Banking77 intent classifier", lifespan=lifespan)


@app.middleware("http")
async def observe(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    REQUESTS.labels(request.method, request.url.path, str(response.status_code)).inc()
    LATENCY.labels(request.url.path).observe(time.perf_counter() - start)
    return response


class PredictRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000)


@app.get("/health")
def health() -> dict:
    if state["model"] is None:
        raise HTTPException(status_code=503, detail={"status": "no model", "error": state["error"]})
    return {
        "status": "ok",
        "source": f"models:/{MODEL_NAME}@{MODEL_ALIAS}",
        "version": state["version"],
        "run_id": state["run_id"],
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/predict")
def predict(req: PredictRequest) -> dict:
    model = state["model"]
    if model is None:
        raise HTTPException(status_code=503, detail="model not loaded")
    proba = model.predict_proba(pd.DataFrame({"text": [req.text]}))[0]
    best = proba.argmax()
    intent = str(model.classes_[best])
    confidence = float(proba[best])
    PREDICTIONS.labels(intent, str(state["version"])).inc()
    CONFIDENCE.observe(confidence)
    return {
        "intent": intent,
        "confidence": round(confidence, 4),
        "model_version": state["version"],
    }
