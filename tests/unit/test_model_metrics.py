"""Unit tests for model metrics + confusion matrix rendering."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ssa_model.metrics import classification_metrics, render_confusion_matrix


def test_classification_metrics_perfect_predictions() -> None:
    y = np.array(["positive", "neutral", "negative", "positive"])
    out = classification_metrics(y, y.copy())
    assert out["accuracy"] == 1.0
    assert out["macro_f1"] == 1.0
    assert out["per_class"]["positive"]["precision"] == 1.0


def test_classification_metrics_all_wrong() -> None:
    y_true = np.array(["positive", "neutral", "negative"])
    y_pred = np.array(["negative", "positive", "neutral"])
    out = classification_metrics(y_true, y_pred)
    assert out["accuracy"] == 0.0
    assert out["macro_f1"] == 0.0


def test_classification_metrics_includes_log_loss() -> None:
    y_true = np.array(["positive", "negative", "neutral"])
    y_pred = np.array(["positive", "negative", "neutral"])
    # Well-calibrated probas
    y_proba = np.array(
        [
            [0.8, 0.1, 0.1],  # positive
            [0.1, 0.1, 0.8],  # negative (column order matches LABELS alphabet)
            [0.1, 0.8, 0.1],  # neutral
        ]
    )
    out = classification_metrics(y_true, y_pred, y_proba)
    assert "log_loss" in out


def test_confusion_matrix_png_is_written(tmp_path: Path) -> None:
    y_true = np.array(["positive", "neutral", "negative", "positive"])
    y_pred = np.array(["positive", "neutral", "neutral", "positive"])
    out = render_confusion_matrix(y_true, y_pred, tmp_path / "cm.png")
    assert out.exists()
    assert out.stat().st_size > 0
