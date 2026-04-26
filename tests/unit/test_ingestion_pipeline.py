"""End-to-end unit test of ingest → validate → eda using a tiny fixture."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ssa_ingestion import eda, pipeline, validation


def _write_seed(tmp_path: Path) -> Path:
    """Write a minimal seed corpus covering every label."""
    records = [
        {
            "id": f"t-{i}",
            "source": "seed",
            "ticker": "AAPL",
            "text": "AAPL had a solid quarter and beat estimates handsomely today.",
            "timestamp": "2026-04-20T10:00:00+00:00",
            "label": "positive",
            "title": None,
            "url": None,
            "author": None,
            "language": "en",
        }
        for i in range(5)
    ]
    records += [
        {
            "id": f"t-{i+5}",
            "source": "seed",
            "ticker": "AAPL",
            "text": "AAPL missed guidance and shares tumbled after the disappointing report.",
            "timestamp": "2026-04-20T11:00:00+00:00",
            "label": "negative",
            "title": None,
            "url": None,
            "author": None,
            "language": "en",
        }
        for i in range(5)
    ]
    seed_path = tmp_path / "data" / "seed" / "seed_corpus.jsonl"
    seed_path.parent.mkdir(parents=True, exist_ok=True)
    with seed_path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    return seed_path


def _write_params(tmp_path: Path) -> Path:
    params_path = tmp_path / "params.yaml"
    params_path.write_text(
        """
ingestion:
  news: { sources: [], lookback_hours: 24, max_items_per_source: 100 }
  social: { sources: [] }
  tickers: [AAPL]
validation:
  min_text_length: 10
  max_text_length: 5000
  dedupe_on: [id, source]
  allowed_languages: [en]
"""
    )
    return params_path


def test_pipeline_end_to_end(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_seed(tmp_path)
    _write_params(tmp_path)

    report = pipeline.run()
    assert report.total_records == 10
    assert report.throughput_rps > 0
    df = pd.read_parquet("data/raw/records.parquet")
    assert len(df) == 10

    vreport = validation.run()
    assert vreport.output_count == 10
    assert vreport.dropped_duplicates == 0
    assert vreport.passed()

    baselines = eda.run()
    assert baselines["sample_size"] == 10
    assert "text_length_chars" in baselines["features"]
    assert baselines["distributions"]["label"] == {"positive": 0.5, "negative": 0.5}
    assert Path("artifacts/baselines.json").exists()
    assert Path("artifacts/eda_summary.md").exists()


def test_validation_dedupes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_params(tmp_path)

    df = pd.DataFrame(
        [
            {
                "id": "dup",
                "source": "seed",
                "ticker": "AAPL",
                "text": "a" * 20,
                "timestamp": "2026-04-20T10:00:00+00:00",
                "label": "positive",
                "title": None,
                "url": None,
                "author": None,
                "language": "en",
            }
        ]
        * 3
    )
    Path("data/raw").mkdir(parents=True, exist_ok=True)
    df.to_parquet("data/raw/records.parquet", index=False)

    report = validation.run()
    assert report.input_count == 3
    assert report.output_count == 1
    assert report.dropped_duplicates == 2


def test_validation_drops_short_text(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_params(tmp_path)

    df = pd.DataFrame(
        [
            {
                "id": "a",
                "source": "seed",
                "ticker": "AAPL",
                "text": "hi",  # below min_text_length=10
                "timestamp": "2026-04-20T10:00:00+00:00",
                "label": "positive",
                "title": None,
                "url": None,
                "author": None,
                "language": "en",
            },
            {
                "id": "b",
                "source": "seed",
                "ticker": "AAPL",
                "text": "this is plenty long text",
                "timestamp": "2026-04-20T10:00:00+00:00",
                "label": "positive",
                "title": None,
                "url": None,
                "author": None,
                "language": "en",
            },
        ]
    )
    Path("data/raw").mkdir(parents=True, exist_ok=True)
    df.to_parquet("data/raw/records.parquet", index=False)

    report = validation.run()
    assert report.dropped_length == 1
    assert report.output_count == 1
