import json
import logging

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import serve
from train import build_model


@pytest.fixture
def client():
    x = pd.DataFrame({"text": ["my card was declined", "card payment failed",
                               "what is the exchange rate", "exchange rate for euros"]})
    model = build_model(ngram_max=1, C=1.0, max_iter=100).fit(x, ["card", "card", "rate", "rate"])
    serve.state.update(model=model, version=0, run_id="test", error=None)  # no MLflow server in CI
    yield TestClient(serve.app)
    serve.state.update(model=None, version=None, run_id=None, error=None)


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_predict_returns_intent(client):
    r = client.post("/predict", json={"text": "my card was declined"})
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "card"
    assert 0.5 < body["confidence"] <= 1.0


def test_empty_text_rejected(client):
    assert client.post("/predict", json={"text": ""}).status_code == 422


def test_health_503_without_model():
    serve.state.update(model=None, error="no model in test")
    assert TestClient(serve.app).get("/health").status_code == 503


def test_metrics_exposes_api_and_model_metrics(client):
    client.post("/predict", json={"text": "my card was declined"})
    r = client.get("/metrics")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    body = r.text
    assert 'banking77_api_requests_total{method="POST",path="/predict",status="200"}' in body
    assert 'banking77_api_request_duration_seconds_bucket{le="+Inf",path="/predict"}' in body
    assert 'banking77_predictions_total{intent="card",model_version="0"}' in body
    assert "banking77_prediction_confidence_count" in body
    

@pytest.fixture
def log_lines():
    lines: list[str] = []

    class ListHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            lines.append(self.format(record))

    handler = ListHandler()
    handler.setFormatter(serve.JsonFormatter())
    serve.logger.addHandler(handler)
    yield lines
    serve.logger.removeHandler(handler)


def test_predict_writes_json_log_line(client, log_lines):
    client.post("/predict", json={"text": "my card was declined"})
    assert len(log_lines) == 1
    entry = json.loads(log_lines[0])
    assert entry["event"] == "request"
    assert entry["path"] == "/predict"
    assert entry["status"] == 200
    assert entry["intent"] == "card"
    assert entry["model_version"] == 0
    assert entry["text"] == "my card was declined"
    assert "request_id" in entry and "duration_ms" in entry


def test_health_is_not_logged(client, log_lines):
    client.get("/health")
    assert log_lines == []