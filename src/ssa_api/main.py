"""FastAPI gateway — Phase 1 stub.

Wires up the service skeleton so the container boots healthy and the
rest of the stack can depend on it. Real routes land in Phase 5.
"""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

logger = structlog.get_logger()

MODEL_SERVER_URL = os.getenv("MODEL_SERVER_URL", "http://model-server:5001")

# --- Metrics ---------------------------------------------------------------
REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.http = httpx.AsyncClient(timeout=5.0)
    logger.info("api_started", model_server_url=MODEL_SERVER_URL)
    try:
        yield
    finally:
        await app.state.http.aclose()


app = FastAPI(title="Stock Sentiment API", version="0.1.0-phase1", lifespan=lifespan)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    with LATENCY.labels(request.method, request.url.path).time():
        response = await call_next(request)
    REQUESTS.labels(request.method, request.url.path, str(response.status_code)).inc()
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status=response.status_code,
    )
    return response


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/ready")
async def ready(request: Request) -> JSONResponse:
    """Ready only if model-server responds to /health."""
    try:
        resp = await request.app.state.http.get(f"{MODEL_SERVER_URL}/health")
        if resp.status_code == 200:
            return JSONResponse({"status": "ready"})
    except httpx.HTTPError as e:
        logger.warning("model_server_unreachable", error=str(e))
    return JSONResponse(
        {"status": "not_ready", "reason": "model_server_unreachable"},
        status_code=503,
    )


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "stock-sentiment-api",
        "version": app.version,
        "docs": "/docs",
    }
