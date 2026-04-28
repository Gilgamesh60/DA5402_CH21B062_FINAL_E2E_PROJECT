"""Client wrapping the model-server HTTP contract.

In production the model-server runs `mlflow models serve` which exposes
`POST /invocations` — the body format is `{"inputs": [...]}` or the
dataframe-split format. We use the `inputs` form because we send text
records.

For the model-server loads a pipeline that accepts raw text;
see `src/ssa_api/inference.py` for the text→prediction adapter.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


class ModelClient:
    def __init__(self, base_url: str, timeout_s: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout_s)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def health(self) -> bool:
        try:
            r = await self._client.get(f"{self.base_url}/health")
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    async def invocations(self, payload: dict[str, Any]) -> Any:
        """Call POST /invocations and return the parsed `predictions` field.

        MLflow models-serve wraps responses as `{"predictions": [...]}`.
        """
        r = await self._client.post(f"{self.base_url}/invocations", json=payload)
        r.raise_for_status()
        body = r.json()
        return body.get("predictions", body)

    async def version(self) -> dict[str, Any] | None:
        try:
            r = await self._client.get(f"{self.base_url}/version")
            if r.status_code == 200:
                return r.json()
        except httpx.HTTPError as e:
            logger.warning("model_version_unavailable", error=str(e))
        return None
