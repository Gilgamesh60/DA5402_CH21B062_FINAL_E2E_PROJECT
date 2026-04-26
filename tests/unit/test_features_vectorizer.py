"""Unit tests for TextFeaturizer and the feature pipeline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ssa_features import pipeline
from ssa_features.vectorizer import TextFeaturizer, VectorizerConfig


def test_fit_transform_produces_nonzero_matrix() -> None:
    f = TextFeaturizer(vectorizer=VectorizerConfig(min_df=1, max_features=50))
    X = f.fit_transform(
        [
            "apple stock surged today",
            "apple stock fell today",
            "microsoft earnings beat expectations",
            "microsoft earnings miss expectations",
        ]
    )
    assert X.shape[0] == 4
    assert X.shape[1] > 0
    assert X.nnz > 0


def test_transform_before_fit_raises() -> None:
    f = TextFeaturizer()
    with pytest.raises(RuntimeError):
        f.transform(["hello"])


def test_metadata_includes_package_version() -> None:
    f = TextFeaturizer(vectorizer=VectorizerConfig(min_df=1))
    f.fit(["hello world", "another doc"])
    meta = f.metadata()
    assert "feature_package_version" in meta
    assert meta["vocab_size"] > 0
    assert meta["vectorizer"]["sublinear_tf"] is True


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    f = TextFeaturizer(vectorizer=VectorizerConfig(min_df=1, max_features=50))
    f.fit(["alpha beta gamma", "beta gamma delta", "delta epsilon zeta"])
    p = tmp_path / "v.joblib"
    f.save(p)
    loaded = TextFeaturizer.load(p)
    X1 = f.transform(["alpha beta"])
    X2 = loaded.transform(["alpha beta"])
    assert (X1 != X2).nnz == 0


def _write_params(tmp_path: Path) -> None:
    (tmp_path / "params.yaml").write_text(
        """
features:
  text_cleaning: {lowercase: true, remove_urls: true, preserve_cashtags: true, remove_mentions: true}
  vectorizer: {max_features: 200, ngram_range: [1, 1], min_df: 1, max_df: 1.0, sublinear_tf: true}
training: {test_size: 0.2, val_size: 0.2, random_seed: 42}
"""
    )


def _make_validated(tmp_path: Path, n: int = 60) -> None:
    labels = (["positive", "negative", "neutral"] * (n // 3 + 1))[:n]
    rows = []
    for i, lbl in enumerate(labels):
        rows.append(
            {
                "id": f"r-{i}",
                "source": "seed",
                "ticker": "AAPL",
                "text": f"sample text number {i} with flavour {lbl}",
                "timestamp": "2026-04-20T10:00:00+00:00",
                "title": None,
                "url": None,
                "author": None,
                "language": "en",
                "label": lbl,
            }
        )
    df = pd.DataFrame(rows)
    (tmp_path / "data/interim").mkdir(parents=True, exist_ok=True)
    df.to_parquet(tmp_path / "data/interim/validated.parquet", index=False)


def test_pipeline_end_to_end_produces_splits_and_vectorizer(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_params(tmp_path)
    _make_validated(tmp_path, n=60)

    report = pipeline.run()
    assert report["splits"]["train"] + report["splits"]["val"] + report["splits"]["test"] == 60
    assert report["featurizer"]["vocab_size"] > 0
    assert Path("data/processed/train.parquet").exists()
    assert Path("data/processed/val.parquet").exists()
    assert Path("data/processed/test.parquet").exists()
    assert Path("artifacts/vectorizer.joblib").exists()

    # Roundtrip: vectorizer can be loaded and used
    fz = TextFeaturizer.load("artifacts/vectorizer.joblib")
    X = fz.transform(["sample text number 99 with flavour positive"])
    assert X.shape == (1, fz.vocab_size_)


def test_pipeline_rejects_unlabelled_data(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_params(tmp_path)
    (tmp_path / "data/interim").mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(
        [
            {
                "id": "a",
                "source": "seed",
                "ticker": "AAPL",
                "text": "hello world",
                "timestamp": "2026-04-20T10:00:00+00:00",
                "title": None,
                "url": None,
                "author": None,
                "language": "en",
                "label": None,
            }
        ]
    )
    df.to_parquet(tmp_path / "data/interim/validated.parquet", index=False)
    with pytest.raises(RuntimeError):
        pipeline.run()
