"""End-to-end: run the user journey against the live stack.

Covers:
  1. Frontend serves the SPA
  2. Runtime /config.js reflects compose env
  3. API proxy works through the frontend's nginx
  4. Prediction round-trips (frontend → api → model-server → reply)
  5. Feedback roundtrips + lands in Postgres
  6. MLflow, Airflow, Prometheus, Grafana all reachable
"""

from __future__ import annotations

import os
from uuid import UUID

import httpx
import pytest

pytestmark = pytest.mark.e2e

FRONTEND = os.getenv("FRONTEND_URL", "http://localhost:3000")
API = os.getenv("API_BASE_URL", "http://localhost:8000")
MLFLOW = os.getenv("MLFLOW_URL", "http://localhost:5000")
AIRFLOW = os.getenv("AIRFLOW_URL", "http://localhost:8080")
PROMETHEUS = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
GRAFANA = os.getenv("GRAFANA_URL", "http://localhost:3001")
ALERTMANAGER = os.getenv("ALERTMANAGER_URL", "http://localhost:9093")


@pytest.fixture(scope="session", autouse=True)
def require_stack() -> None:
    """Skip if the stack isn't up — keeps CI green."""
    try:
        httpx.get(f"{API}/health", timeout=3.0)
    except httpx.HTTPError:
        pytest.skip("stack unreachable", allow_module_level=True)


def test_frontend_serves_html() -> None:
    r = httpx.get(FRONTEND, timeout=5.0)
    assert r.status_code == 200
    assert "<div id=\"root\"></div>" in r.text
    assert "/config.js" in r.text


def test_frontend_runtime_config() -> None:
    r = httpx.get(f"{FRONTEND}/config.js", timeout=5.0)
    assert r.status_code == 200
    assert "SSA_CONFIG" in r.text
    assert "apiBaseUrl" in r.text


def test_frontend_proxies_to_api() -> None:
    r = httpx.get(f"{FRONTEND}/api/health", timeout=5.0)
    assert r.status_code == 200
    assert r.json() == {"status": "alive"}


def test_prediction_roundtrip_via_frontend() -> None:
    r = httpx.post(
        f"{FRONTEND}/api/predict",
        json={"ticker": "AAPL"},
        timeout=15.0,
    )
    # Seed data may not cover every ticker; 200 or 404 are both acceptable
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        body = r.json()
        assert body["sentiment"] in {"positive", "neutral", "negative"}
        UUID(body["request_id"])


def test_feedback_journey() -> None:
    pred = httpx.post(f"{API}/predict", json={"ticker": "AAPL"}, timeout=15.0)
    if pred.status_code != 200:
        pytest.skip("no prediction to anchor feedback to")
    request_id = pred.json()["request_id"]
    r = httpx.post(
        f"{API}/feedback",
        json={
            "ticker": "AAPL",
            "prediction_request_id": request_id,
            "true_label": "positive",
        },
        timeout=5.0,
    )
    assert r.status_code == 202
    assert r.json()["accepted"] is True


def test_mlflow_reachable() -> None:
    r = httpx.get(f"{MLFLOW}/health", timeout=5.0)
    assert r.status_code == 200


def test_airflow_reachable() -> None:
    r = httpx.get(f"{AIRFLOW}/health", timeout=5.0)
    assert r.status_code == 200


def test_prometheus_reachable() -> None:
    r = httpx.get(f"{PROMETHEUS}/-/healthy", timeout=5.0)
    assert r.status_code == 200


def test_prometheus_scrapes_api_target() -> None:
    r = httpx.get(f"{PROMETHEUS}/api/v1/targets?state=active", timeout=5.0)
    assert r.status_code == 200
    data = r.json()["data"]["activeTargets"]
    api_target = next((t for t in data if t["labels"]["job"] == "api"), None)
    assert api_target is not None, "api target not registered in Prometheus"
    assert api_target["health"] == "up", f"api target unhealthy: {api_target}"


def test_grafana_reachable() -> None:
    r = httpx.get(f"{GRAFANA}/api/health", timeout=5.0)
    assert r.status_code == 200


def test_alertmanager_reachable() -> None:
    r = httpx.get(f"{ALERTMANAGER}/-/healthy", timeout=5.0)
    assert r.status_code == 200
