-- Create separate logical databases for each subsystem that needs its own.
-- The default POSTGRES_DB (mlops) holds application tables.

CREATE DATABASE mlflow;
CREATE DATABASE airflow;

\c mlops;

-- pgcrypto provides gen_random_uuid
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------
-- Predictions log: one row per /predict or /batch_predict invocation
-- so /feedback can join back to the predicted label and we can compute
-- real-world accuracy from submitted ground truth.
-- ---------------------------------------------------------------
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

-- ---------------------------------------------------------------
-- Feedback: ground-truth labels submitted from the UI
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS feedback (
    feedback_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(10) NOT NULL,
    prediction_request_id UUID NOT NULL,
    true_label VARCHAR(16) NOT NULL CHECK (true_label IN ('positive', 'negative', 'neutral')),
    predicted_label VARCHAR(16),
    user_comment TEXT,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_feedback_prediction
        FOREIGN KEY (prediction_request_id)
        REFERENCES predictions(prediction_request_id)
        DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX IF NOT EXISTS idx_feedback_ticker ON feedback(ticker);
CREATE INDEX IF NOT EXISTS idx_feedback_received_at ON feedback(received_at);
