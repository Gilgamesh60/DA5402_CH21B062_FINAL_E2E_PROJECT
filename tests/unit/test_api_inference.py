"""Unit tests for ssa_api.inference aggregation logic."""

from __future__ import annotations

import pytest

from ssa_api.inference import aggregate, summarise_class_counts
from ssa_api.schemas import Sentiment


def _p(sentiment: str, pos: float, neu: float, neg: float, conf: float | None = None) -> dict:
    return {
        "sentiment": sentiment,
        "confidence": conf if conf is not None else max(pos, neu, neg),
        "scores": {"positive": pos, "neutral": neu, "negative": neg},
    }


def test_aggregate_picks_max_average() -> None:
    preds = [_p("positive", 0.8, 0.1, 0.1), _p("positive", 0.7, 0.2, 0.1)]
    rows = [{"source": "seed", "text": "a"}, {"source": "seed", "text": "b"}]
    sentiment, conf, scores, exps = aggregate(preds, rows)
    assert sentiment == Sentiment.POSITIVE
    assert pytest.approx(scores.positive, rel=1e-3) == 0.75
    assert pytest.approx(scores.neutral, rel=1e-3) == 0.15
    assert pytest.approx(scores.negative, rel=1e-3) == 0.10
    assert conf == pytest.approx(0.75, rel=1e-3)
    assert exps == []


def test_aggregate_renormalises_to_sum_one() -> None:
    preds = [_p("neutral", 0.1, 0.4, 0.5)]
    rows = [{"source": "seed", "text": "x"}]
    sentiment, conf, scores, _ = aggregate(preds, rows)
    assert sentiment == Sentiment.NEGATIVE
    assert pytest.approx(scores.positive + scores.neutral + scores.negative, rel=1e-3) == 1.0


def test_aggregate_with_explanations() -> None:
    preds = [
        _p("positive", 0.9, 0.05, 0.05),
        _p("positive", 0.6, 0.3, 0.1),
        _p("negative", 0.1, 0.2, 0.7),
    ]
    rows = [
        {"source": "news", "text": "great earnings beat"},
        {"source": "news", "text": "analysts upgrade"},
        {"source": "reddit", "text": "bearish thread"},
    ]
    sentiment, _, _, exps = aggregate(preds, rows, include_explanations=True, top_n_explanations=2)
    assert sentiment == Sentiment.POSITIVE
    assert len(exps) == 2
    assert exps[0].contribution >= exps[1].contribution


def test_aggregate_empty_raises() -> None:
    with pytest.raises(ValueError):
        aggregate([], [])


def test_summarise_class_counts() -> None:
    preds = [
        _p("positive", 0.8, 0.1, 0.1),
        _p("positive", 0.7, 0.2, 0.1),
        _p("negative", 0.1, 0.1, 0.8),
    ]
    c = summarise_class_counts(preds)
    assert c == {"positive": 2, "negative": 1}
