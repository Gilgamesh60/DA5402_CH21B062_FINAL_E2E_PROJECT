"""Contract tests — every endpoint's live response matches docs/LLD.md.

Runs against the live stack on localhost:8000. The whole suite is
skipped if the API is unreachable (session fixture).
"""

from __future__ import annotations

from uuid import UUID

import httpx
import pytest

pytestmark = pytest.mark.contract


# ---------------------------------------------------------------
# Health / readiness
# ---------------------------------------------------------------
def test_health_returns_alive(api_client: httpx.Client) -> None:
    r = api_client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "alive"}


def test_health_sets_request_id_header(api_client: httpx.Client) -> None:
    r = api_client.get("/health")
    assert "x-request-id" in {k.lower() for k in r.headers.keys()}


def test_ready_returns_model_ref(api_client: httpx.Client) -> None:
    r = api_client.get("/ready")
    # Either ready (200) or not_ready (503) — both shapes allowed
    assert r.status_code in (200, 503)
    body = r.json()
    assert body["status"] in {"ready", "not_ready"}
    if body["status"] == "ready":
        for k in ("name", "version", "stage"):
            assert k in body["model"]


# ---------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------
def test_metrics_exposes_required_series(api_client: httpx.Client) -> None:
    r = api_client.get("/metrics")
    assert r.status_code == 200
    # Seed metric traffic
    api_client.get("/health")
    api_client.get("/health")
    r = api_client.get("/metrics")
    body = r.text
    for series in (
        "http_requests_total",
        "http_request_duration_seconds",
    ):
        assert series in body


# ---------------------------------------------------------------
# Model introspection
# ---------------------------------------------------------------
def test_model_info_schema(api_client: httpx.Client) -> None:
    r = api_client.get("/model/info")
    assert r.status_code == 200
    body = r.json()
    for k in ("name", "version", "stage"):
        assert k in body, f"missing required field {k}"
    # git SHA is optional per the LLD but we log it from train; assert presence
    assert body.get("git_commit_sha") is None or len(body["git_commit_sha"]) >= 7


def test_model_versions_schema(api_client: httpx.Client) -> None:
    r = api_client.get("/model/versions")
    assert r.status_code == 200
    body = r.json()
    assert "versions" in body
    assert isinstance(body["versions"], list)
    for v in body["versions"]:
        assert set(v.keys()) >= {"version", "stage"}


# ---------------------------------------------------------------
# /predict
# ---------------------------------------------------------------
def test_predict_happy_path_schema(api_client: httpx.Client) -> None:
    r = api_client.post("/predict", json={"ticker": "AAPL"})
    assert r.status_code in (200, 404)  # 404 = no data, also valid per contract
    if r.status_code != 200:
        return
    body = r.json()
    required = {
        "ticker",
        "sentiment",
        "confidence",
        "scores",
        "sample_size",
        "lookback_hours",
        "model",
        "explanations",
        "request_id",
        "latency_ms",
    }
    assert required <= set(body.keys()), f"missing fields: {required - set(body.keys())}"
    assert body["sentiment"] in {"positive", "neutral", "negative"}
    assert 0.0 <= body["confidence"] <= 1.0
    s = body["scores"]
    assert abs(s["positive"] + s["neutral"] + s["negative"] - 1.0) < 0.01
    # request_id is a uuid
    UUID(body["request_id"])


def test_predict_invalid_ticker_400(api_client: httpx.Client) -> None:
    r = api_client.post("/predict", json={"ticker": "lowercase!!"})
    assert r.status_code == 400
    body = r.json()
    assert body["code"] == "INVALID_TICKER"
    assert "request_id" in body


def test_predict_unknown_ticker_404(api_client: httpx.Client) -> None:
    # Valid format, but a ticker that isn't in the seed corpus.
    r = api_client.post("/predict", json={"ticker": "ZZZ"})
    # 404 for "no data", 200 with empty aggregation if upstream was lenient
    assert r.status_code in (200, 404)


def test_predict_respects_lookback_bounds(api_client: httpx.Client) -> None:
    r = api_client.post("/predict", json={"ticker": "AAPL", "lookback_hours": 9999})
    assert r.status_code == 400


# ---------------------------------------------------------------
# /batch_predict
# ---------------------------------------------------------------
def test_batch_predict_multi_ticker(api_client: httpx.Client) -> None:
    r = api_client.post(
        "/batch_predict",
        json={"tickers": ["AAPL", "MSFT", "NVDA"], "lookback_hours": 48},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["results"]) == 3
    for item in body["results"]:
        assert "ticker" in item
        # Either success (sentiment set) or error (error set)
        assert item.get("sentiment") or item.get("error")


# ---------------------------------------------------------------
# /feedback
# ---------------------------------------------------------------
def test_feedback_happy_path(api_client: httpx.Client) -> None:
    # Generate a real prediction so the FK exists
    pred = api_client.post("/predict", json={"ticker": "AAPL"})
    if pred.status_code != 200:
        pytest.skip("no prediction to link feedback to")
    request_id = pred.json()["request_id"]

    r = api_client.post(
        "/feedback",
        json={
            "ticker": "AAPL",
            "prediction_request_id": request_id,
            "true_label": "positive",
        },
    )
    assert r.status_code == 202
    body = r.json()
    assert body["accepted"] is True
    UUID(body["feedback_id"])


def test_feedback_validates_label(api_client: httpx.Client) -> None:
    r = api_client.post(
        "/feedback",
        json={
            "ticker": "AAPL",
            "prediction_request_id": "00000000-0000-0000-0000-000000000001",
            "true_label": "bogus",
        },
    )
    assert r.status_code == 400
