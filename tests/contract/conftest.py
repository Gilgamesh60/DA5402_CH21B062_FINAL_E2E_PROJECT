"""Contract tests run against the live API. Fixtures here handle base URL + skip."""

from __future__ import annotations

import os

import httpx
import pytest

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def api_client() -> httpx.Client:
    with httpx.Client(base_url=API_BASE, timeout=10.0) as c:
        yield c


@pytest.fixture(scope="session", autouse=True)
def require_live_api(api_client: httpx.Client) -> None:
    """Skip the whole contract suite if the API isn't up."""
    try:
        r = api_client.get("/health")
    except httpx.HTTPError:
        pytest.skip("API not reachable at " + API_BASE, allow_module_level=True)
    if r.status_code != 200:
        pytest.skip(f"API health returned {r.status_code}", allow_module_level=True)
