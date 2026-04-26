"""Inference orchestration.

Takes a ticker, pulls recent records, forwards each text to the
model-server, and aggregates the per-record predictions into a single
ticker-level sentiment (argmax over averaged probabilities).
"""

from __future__ import annotations

from collections import Counter
from typing import Any

import structlog

from ssa_api.model_client import ModelClient
from ssa_api.schemas import Explanation, Sentiment, SentimentScores

logger = structlog.get_logger()

LABELS = ("positive", "neutral", "negative")


async def predict_for_texts(
    client: ModelClient, texts: list[str]
) -> list[dict[str, Any]]:
    """Ask the model-server to predict each text. Returns a list of dicts."""
    if not texts:
        return []
    # MLflow pyfunc /invocations accepts `{"inputs": [{"text": "..."}]}`
    payload = {"inputs": [{"text": t} for t in texts]}
    predictions = await client.invocations(payload)
    if not isinstance(predictions, list):
        raise ValueError(f"unexpected model-server response: {type(predictions)}")
    return predictions


def aggregate(
    predictions: list[dict[str, Any]],
    records: list[dict[str, Any]],
    include_explanations: bool = False,
    top_n_explanations: int = 5,
) -> tuple[Sentiment, float, SentimentScores, list[Explanation]]:
    """Aggregate per-record predictions into a single ticker-level answer.

    Returns (sentiment, confidence, scores, explanations).
    """
    if not predictions:
        raise ValueError("aggregate called with empty predictions")

    totals = {lbl: 0.0 for lbl in LABELS}
    for p in predictions:
        scores = p.get("scores") or {}
        for lbl in LABELS:
            totals[lbl] += float(scores.get(lbl, 0.0))
    n = len(predictions)
    avg = {lbl: round(totals[lbl] / n, 6) for lbl in LABELS}
    # Renormalise so the three sum to 1.0 exactly (handles rounding drift).
    s = sum(avg.values()) or 1.0
    avg = {k: round(v / s, 6) for k, v in avg.items()}

    top_label, top_score = max(avg.items(), key=lambda kv: kv[1])
    scores = SentimentScores(positive=avg["positive"], neutral=avg["neutral"], negative=avg["negative"])

    # Confidence = probability of the winning class (simple, defensible)
    confidence = round(top_score, 6)

    explanations: list[Explanation] = []
    if include_explanations:
        # Pick the top N records whose predicted label matches the aggregate
        # and whose confidence is highest — crude but useful.
        paired = list(zip(predictions, records))
        same_label = [(p, r) for p, r in paired if p.get("sentiment") == top_label]
        same_label.sort(key=lambda pr: pr[0].get("confidence", 0.0), reverse=True)
        for pred, rec in same_label[:top_n_explanations]:
            explanations.append(
                Explanation(
                    source=str(rec.get("source", "unknown")),
                    snippet=str(rec.get("text", ""))[:200],
                    contribution=round(float(pred.get("confidence", 0.0)), 4),
                )
            )

    return Sentiment(top_label), confidence, scores, explanations


def summarise_class_counts(predictions: list[dict[str, Any]]) -> dict[str, int]:
    """Count of argmax labels — used for the `predictions_total` metric."""
    c: Counter[str] = Counter()
    for p in predictions:
        c[p.get("sentiment", "unknown")] += 1
    return dict(c)
