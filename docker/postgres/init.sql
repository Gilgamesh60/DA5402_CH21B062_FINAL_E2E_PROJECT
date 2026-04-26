-- Create separate logical databases for each subsystem that needs its own.
-- The default POSTGRES_DB (mlops) holds the feedback table.

CREATE DATABASE mlflow;
CREATE DATABASE airflow;

-- Feedback table lives in the default mlops database.
\c mlops;

CREATE TABLE IF NOT EXISTS feedback (
    feedback_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(10) NOT NULL,
    prediction_request_id UUID NOT NULL,
    true_label VARCHAR(16) NOT NULL CHECK (true_label IN ('positive', 'negative', 'neutral')),
    predicted_label VARCHAR(16),
    user_comment TEXT,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feedback_ticker ON feedback(ticker);
CREATE INDEX IF NOT EXISTS idx_feedback_received_at ON feedback(received_at);

-- pgcrypto for gen_random_uuid
CREATE EXTENSION IF NOT EXISTS pgcrypto;
