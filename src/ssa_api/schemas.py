"""Pydantic request/response schemas.

These are the single source of truth for the API contract — FastAPI
auto-generates the OpenAPI spec from them, and the contents match
`docs/LLD.md` exactly.
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class ErrorCode(str, Enum):
    INVALID_TICKER = "INVALID_TICKER"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    RATE_LIMITED = "RATE_LIMITED"
    NO_DATA = "NO_DATA"
    INTERNAL = "INTERNAL"


# ---------------------------------------------------------------------------
# Common
# ---------------------------------------------------------------------------
class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    error: str
    code: ErrorCode
    request_id: str
    details: dict | None = None


class ModelRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    version: str
    stage: str


class ModelInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    version: str
    stage: str
    git_commit_sha: str | None = None
    mlflow_run_id: str | None = None
    data_hash: str | None = None
    trained_at: datetime | None = None


# ---------------------------------------------------------------------------
# /health, /ready
# ---------------------------------------------------------------------------
class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["alive"]


class ReadyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ready"]
    model: ModelRef


class NotReadyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["not_ready"]
    reason: str


# ---------------------------------------------------------------------------
# /predict
# ---------------------------------------------------------------------------
class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticker: str = Field(..., min_length=1, max_length=10)
    lookback_hours: int = Field(24, ge=1, le=168)
    include_explanations: bool = False

    @field_validator("ticker")
    @classmethod
    def _validate_ticker(cls, v: str) -> str:
        v = v.strip().upper()
        if not TICKER_RE.match(v):
            raise ValueError(f"invalid ticker: {v!r}")
        return v


class SentimentScores(BaseModel):
    model_config = ConfigDict(extra="forbid")
    positive: float
    neutral: float
    negative: float


class Explanation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str
    snippet: str
    contribution: float


class PredictResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticker: str
    sentiment: Sentiment
    confidence: float = Field(..., ge=0.0, le=1.0)
    scores: SentimentScores
    sample_size: int
    lookback_hours: int
    model: ModelRef
    explanations: list[Explanation] = Field(default_factory=list)
    request_id: str
    latency_ms: int


# ---------------------------------------------------------------------------
# /batch_predict
# ---------------------------------------------------------------------------
class BatchPredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tickers: list[str] = Field(..., min_length=1, max_length=50)
    lookback_hours: int = Field(24, ge=1, le=168)

    @field_validator("tickers")
    @classmethod
    def _validate_tickers(cls, v: list[str]) -> list[str]:
        out = []
        for t in v:
            t = t.strip().upper()
            if not TICKER_RE.match(t):
                raise ValueError(f"invalid ticker: {t!r}")
            out.append(t)
        return out


class BatchItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticker: str
    sentiment: Sentiment | None = None
    confidence: float | None = None
    scores: SentimentScores | None = None
    sample_size: int | None = None
    error: dict | None = None


class BatchPredictResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    results: list[BatchItem]
    model: ModelRef
    request_id: str
    latency_ms: int


# ---------------------------------------------------------------------------
# /feedback
# ---------------------------------------------------------------------------
class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticker: str = Field(..., min_length=1, max_length=10)
    prediction_request_id: UUID
    true_label: Sentiment
    user_comment: str | None = Field(None, max_length=500)

    @field_validator("ticker")
    @classmethod
    def _validate_ticker(cls, v: str) -> str:
        v = v.strip().upper()
        if not TICKER_RE.match(v):
            raise ValueError(f"invalid ticker: {v!r}")
        return v


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    accepted: bool
    feedback_id: UUID


# ---------------------------------------------------------------------------
# /model/versions, /model/rollback
# ---------------------------------------------------------------------------
class VersionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    stage: str
    trained_at: datetime | None = None
    macro_f1: float | None = None


class VersionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    versions: list[VersionSummary]


class RollbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_version: str


class RollbackResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    previous: ModelRef
    current: ModelRef
    reload_triggered: bool
