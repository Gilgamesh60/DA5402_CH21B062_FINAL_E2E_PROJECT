"""Source adapters. Each implements the `Source` protocol.

Live adapters (NewsAPI, Finnhub, Reddit) are optional — only loaded
when their keys are present. The `SeedSource` is always available
so the pipeline is runnable offline.
"""

from __future__ import annotations

from .base import DataSource
from .seed import SeedSource

__all__ = ["DataSource", "SeedSource"]
