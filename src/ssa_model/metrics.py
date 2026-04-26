"""Evaluation metrics + artifact rendering.

Every training run logs these, and the evaluate stage re-uses them
on the held-out test split.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_recall_fscore_support,
)

LABELS = ["positive", "neutral", "negative"]


def classification_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray | None = None,
    labels: list[str] | None = None,
) -> dict[str, Any]:
    """Headline metrics MLflow + evaluate stage both consume."""
    labels = labels or LABELS
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0
    )
    macro = f1_score(y_true, y_pred, average="macro", zero_division=0)
    weighted = f1_score(y_true, y_pred, average="weighted", zero_division=0)
    acc = accuracy_score(y_true, y_pred)

    out: dict[str, Any] = {
        "accuracy": round(float(acc), 6),
        "macro_f1": round(float(macro), 6),
        "weighted_f1": round(float(weighted), 6),
        "per_class": {
            lbl: {
                "precision": round(float(precision[i]), 6),
                "recall": round(float(recall[i]), 6),
                "f1": round(float(f1[i]), 6),
            }
            for i, lbl in enumerate(labels)
        },
        "classification_report": classification_report(
            y_true, y_pred, labels=labels, zero_division=0, digits=4
        ),
    }
    if y_proba is not None:
        try:
            out["log_loss"] = round(float(log_loss(y_true, y_proba, labels=labels)), 6)
        except Exception:
            pass
    return out


def render_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    out_path: Path | str,
    labels: list[str] | None = None,
) -> Path:
    """PNG for MLflow. Uses matplotlib; kept minimal to avoid heavy deps."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = labels or LABELS
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    fig, ax = plt.subplots(figsize=(5, 4))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_yticklabels(labels)
    ax.set_xlabel("predicted")
    ax.set_ylabel("true")
    ax.set_title("Confusion matrix")
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, str(cm[i][j]), ha="center", va="center",
                    color="white" if cm[i][j] > cm.max() / 2 else "black")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    return out_path
