"""Phase 1 stub model server.

Mimics the MLflow `models serve` HTTP contract so that the API gateway
and healthchecks can wire against a stable interface. Replaced in Phase
4 by `mlflow models serve -m models:/stock-sentiment/Production`.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Model Server (Phase 1 stub)", version="0.1.0-phase1")


class Invocation(BaseModel):
    inputs: list[dict[str, Any]] | list[list[Any]] | dict[str, Any]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/version")
async def version() -> dict[str, str]:
    return {"name": "stub", "version": "0.0.0", "stage": "none"}


@app.post("/invocations")
async def invocations(body: Invocation) -> dict[str, list[dict[str, Any]]]:
    # Always returns neutral in Phase 1 so the end-to-end path is provable.
    return {
        "predictions": [
            {"sentiment": "neutral", "confidence": 0.5}
        ]
    }
