"""Data access for the API gateway.

- FeedbackRepo writes ground-truth labels to Postgres.
- PredictionRepo writes prediction events so /feedback can join back to
  the predicted label and we can compute real-world accuracy.
- RecordRepo reads recent text records for a ticker. reads from
  the validated parquet; (live data) switches to a proper store.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pandas as pd
import psycopg2
import structlog

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Predictions
# ---------------------------------------------------------------------------
class PredictionRepo:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self._conn = None

    def _get_conn(self):
        """Lazy single connection, auto-reconnect on failure.

        A connection pool would be nicer but adds a dep; we only have one
        process and a single worker so one long-lived conn is fine.
        """
        try:
            if self._conn is None or self._conn.closed:
                self._conn = psycopg2.connect(self.dsn)
            return self._conn
        except Exception:
            self._conn = psycopg2.connect(self.dsn)
            return self._conn

    def insert(
        self,
        prediction_request_id: UUID | str,
        ticker: str,
        predicted_label: str,
        confidence: float,
        model_version: str | None,
        model_stage: str | None,
        sample_size: int | None,
        lookback_hours: int | None,
        latency_ms: int | None,
    ) -> None:
        sql = (
            "INSERT INTO predictions "
            "(prediction_request_id, ticker, predicted_label, confidence, "
            " model_version, model_stage, sample_size, lookback_hours, latency_ms) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (prediction_request_id) DO NOTHING"
        )
        params = (
            str(prediction_request_id),
            ticker,
            predicted_label,
            float(confidence),
            model_version,
            model_stage,
            sample_size,
            lookback_hours,
            latency_ms,
        )
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute(sql, params)
            conn.commit()
        except Exception as e:
            # Never let logging-side failures kill a prediction request.
            logger.warning("prediction_log_failed", error=str(e))
            # Reset conn on error so next call reconnects
            try:
                if self._conn is not None:
                    self._conn.close()
            except Exception:
                pass
            self._conn = None


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------
class FeedbackRepo:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def insert(
        self,
        ticker: str,
        prediction_request_id: UUID,
        true_label: str,
        predicted_label: str | None,
        user_comment: str | None,
    ) -> UUID:
        feedback_id = uuid4()
        sql = (
            "INSERT INTO feedback "
            "(feedback_id, ticker, prediction_request_id, true_label, "
            "predicted_label, user_comment, received_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)"
        )
        params = (
            str(feedback_id),
            ticker,
            str(prediction_request_id),
            true_label,
            predicted_label,
            user_comment,
            datetime.now(timezone.utc),
        )
        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
            conn.commit()
        return feedback_id


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------
class RecordRepo:
    """Reads the validated records parquet and filters by ticker + window."""

    DEFAULT_PATH = Path("data/interim/validated.parquet")

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path else self.DEFAULT_PATH
        self._cache: pd.DataFrame | None = None
        self._cache_mtime: float = 0.0

    def _load(self) -> pd.DataFrame:
        """Lazy-load the parquet, reloading only when mtime changes."""
        if not self.path.exists():
            return pd.DataFrame(
                columns=["id", "source", "ticker", "text", "timestamp", "label"]
            )
        mtime = self.path.stat().st_mtime
        if self._cache is None or mtime != self._cache_mtime:
            df = pd.read_parquet(self.path)
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            self._cache = df
            self._cache_mtime = mtime
        return self._cache

    def recent(self, ticker: str, lookback_hours: int) -> list[dict[str, Any]]:
        df = self._load()
        if df.empty:
            return []
        since = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        # For the seed dataset the timestamps are historical, so fall back
        # to the most recent N records for the ticker when nothing is
        # in the last `lookback_hours`. Keeps the demo deterministic.
        subset = df[(df["ticker"] == ticker)]
        if subset.empty:
            return []
        recent = subset[subset["timestamp"] >= since]
        if recent.empty:
            recent = subset.sort_values("timestamp", ascending=False).head(50)
        return recent.to_dict(orient="records")
