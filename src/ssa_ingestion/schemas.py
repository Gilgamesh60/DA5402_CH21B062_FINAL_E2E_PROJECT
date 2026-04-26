"""Shared Pydantic schemas for ingested records.

A single `TextRecord` type normalises news articles and social posts so
downstream stages (features, training) see one shape.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


class Source(str, Enum):
    """Origin of a text record."""

    NEWSAPI = "newsapi"
    FINNHUB = "finnhub"
    REDDIT = "reddit"
    SEED = "seed"


class SentimentLabel(str, Enum):
    """Closed set of sentiment labels matching the API contract."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class TextRecord(BaseModel):
    """Normalised text record consumed by the feature pipeline."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(..., min_length=1, max_length=128, description="Stable source-scoped id")
    source: Source
    ticker: str = Field(..., min_length=1, max_length=10)
    text: str = Field(..., min_length=1, max_length=5000)
    timestamp: datetime = Field(..., description="UTC timestamp of the original item")
    title: str | None = Field(None, max_length=512)
    url: str | None = Field(None, max_length=1024)
    author: str | None = Field(None, max_length=128)
    language: str = Field("en", min_length=2, max_length=5)
    label: SentimentLabel | None = Field(
        None,
        description="Optional ground-truth label for supervised training data.",
    )

    @field_validator("ticker")
    @classmethod
    def _upper_ticker(cls, v: str) -> str:
        v = v.strip().upper()
        if not TICKER_RE.match(v):
            raise ValueError(f"invalid ticker: {v!r}")
        return v

    @field_validator("timestamp")
    @classmethod
    def _ensure_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    def key(self) -> tuple[str, str]:
        """Dedup key — stable across runs."""
        return (self.source.value, self.id)


class IngestionReport(BaseModel):
    """Summary of an ingestion run — emitted as JSON artifact."""

    model_config = ConfigDict(extra="forbid")

    started_at: datetime
    finished_at: datetime
    sources: dict[str, int] = Field(default_factory=dict)
    total_records: int = 0
    duration_seconds: float = 0.0
    throughput_rps: float = 0.0
    errors: list[str] = Field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class ValidationReport(BaseModel):
    """Summary of a validation run."""

    model_config = ConfigDict(extra="forbid")

    input_count: int
    output_count: int
    dropped_schema_errors: int = 0
    dropped_duplicates: int = 0
    dropped_length: int = 0
    dropped_language: int = 0
    per_ticker: dict[str, int] = Field(default_factory=dict)
    per_source: dict[str, int] = Field(default_factory=dict)

    def passed(self) -> bool:
        """Validation passes if at least one record survives."""
        return self.output_count > 0
