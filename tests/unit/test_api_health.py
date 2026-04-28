"""Unit tests for the API — probes and Prometheus exposition."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ssa_api.main import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_health_returns_200_alive(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "alive"}


def test_root_returns_service_metadata(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "stock-sentiment-api"
    assert body["docs"] == "/docs"


def test_metrics_endpoint_is_prometheus_format(client: TestClient) -> None:
    client.get("/health")
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "http_requests_total" in r.text
    assert "http_request_duration_seconds" in r.text


def test_request_id_header_is_set(client: TestClient) -> None:
    r = client.get("/health")
    assert "x-request-id" in {k.lower() for k in r.headers.keys()}


def test_predict_validation_rejects_bad_ticker(client: TestClient) -> None:
    r = client.post("/predict", json={"ticker": "lowercase!!"})
    assert r.status_code == 400
    body = r.json()
    assert body["code"] == "INVALID_TICKER"
