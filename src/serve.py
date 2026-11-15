"""Inference API: loads models:/banking77@champion from the cluster MLflow at start-up.

MLFLOW_TRACKING_URI=http://127.0.0.1:5005 uvicorn serve:app --app-dir src --port 8000
"""

import os
from contextlib import asynccontextmanager

import mlflow
import pandas as pd
from fastapi import FastAPI, HTTPException
from mlflow import MlflowClient
from pydantic import BaseModel, Field

MODEL_NAME = os.environ.get("MODEL_NAME", "banking77")
MODEL_ALIAS = os.environ.get("MODEL_ALIAS", "champion")

state = {"model": None, "version": None, "run_id": None, "error": None}


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


@app.post("/predict")
def predict(req: PredictRequest) -> dict:
    model = state["model"]
    if model is None:
        raise HTTPException(status_code=503, detail="model not loaded")
    proba = model.predict_proba(pd.DataFrame({"text": [req.text]}))[0]
    best = proba.argmax()
    return {
        "intent": str(model.classes_[best]),
        "confidence": round(float(proba[best]), 4),
        "model_version": state["version"],
    }
