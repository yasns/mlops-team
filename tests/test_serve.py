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
