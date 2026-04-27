-- Phase 9: add predictions table and link feedback to it.
-- Safe to run multiple times (IF NOT EXISTS everywhere).

\c mlops;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS predictions (
    prediction_request_id UUID PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    predicted_label VARCHAR(16) NOT NULL CHECK (predicted_label IN ('positive', 'neutral', 'negative')),
    confidence REAL NOT NULL,
    model_version VARCHAR(32),
    model_stage VARCHAR(16),
    sample_size INTEGER,
    lookback_hours INTEGER,
    latency_ms INTEGER,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_predictions_ticker ON predictions(ticker);
CREATE INDEX IF NOT EXISTS idx_predictions_issued_at ON predictions(issued_at);
CREATE INDEX IF NOT EXISTS idx_predictions_version ON predictions(model_version);
