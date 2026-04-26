"""Request-logging + metrics middleware.

- Assigns/propagates a request id on every request.
- Emits structured JSON logs on every response.
- Records Prometheus histogram + counter for every (method, path, status).
- Adds `X-Request-ID` to every response.
"""

from __future__ import annotations

import time
import uuid

import structlog
from fastapi import Request
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()

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


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id
        t0 = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - t0
        route = request.scope.get("route")
        path = route.path if route else request.url.path
        LATENCY.labels(request.method, path).observe(elapsed)
        REQUESTS.labels(request.method, path, str(response.status_code)).inc()
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request",
            request_id=request_id,
            method=request.method,
            path=path,
            status=response.status_code,
            latency_ms=int(elapsed * 1000),
        )
        return response
