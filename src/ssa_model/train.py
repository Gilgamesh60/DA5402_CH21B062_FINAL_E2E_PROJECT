"""Train a sentiment classifier — Phase 4 baseline.

Loads the Phase 3 feature splits + vectorizer, trains a logistic
regression, logs everything to MLflow, registers the model. Writes
`artifacts/train_metrics.json` so DVC can track it as a metric.
"""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
import structlog
import yaml
from sklearn.linear_model import LogisticRegression

from ssa_features.vectorizer import TextFeaturizer
from ssa_model import __version__ as model_pkg_version
from ssa_model.metrics import classification_metrics, render_confusion_matrix
from ssa_model.tracking import configure_mlflow, mlflow_run

logger = structlog.get_logger()

TRAIN_METRICS_OUT = Path("artifacts/train_metrics.json")
MODEL_URI_OUT = Path("artifacts/model_uri.txt")


@dataclass
class TrainingConfig:
    model_type: str = "logistic_regression"
    class_weight: str = "balanced"
    C: float = 1.0
    max_iter: int = 1000
    random_seed: int = 42
    registry_name: str = "stock-sentiment"

    @classmethod
    def from_file(cls, path: Path | str = "params.yaml") -> "TrainingConfig":
        with Path(path).open("r", encoding="utf-8") as fh:
            raw: dict[str, Any] = yaml.safe_load(fh)
        tr = raw.get("training", {})
        hp = tr.get("hyperparameters", {})
        reg = raw.get("registry", {})
        return cls(
            model_type=tr.get("model_type", "logistic_regression"),
            class_weight=tr.get("class_weight", "balanced"),
            C=float(hp.get("C", 1.0)),
            max_iter=int(hp.get("max_iter", 1000)),
            random_seed=int(tr.get("random_seed", 42)),
            registry_name=str(reg.get("model_name", "stock-sentiment")),
        )


def _build_classifier(cfg: TrainingConfig) -> LogisticRegression:
    if cfg.model_type != "logistic_regression":
        raise NotImplementedError(
            f"Phase 4 baseline only supports logistic_regression; got {cfg.model_type}"
        )
    return LogisticRegression(
        C=cfg.C,
        max_iter=cfg.max_iter,
        class_weight=cfg.class_weight,
        random_state=cfg.random_seed,
        solver="lbfgs",
    )


def _top_feature_importances(
    clf: LogisticRegression, feature_names: np.ndarray, n: int = 20
) -> dict[str, list[dict[str, float]]]:
    """Top positive + top negative tokens per class for explainability."""
    out: dict[str, list[dict[str, float]]] = {}
    classes = clf.classes_
    coefs = clf.coef_
    for i, cls in enumerate(classes):
        weights = coefs[i]
        top_idx = np.argsort(weights)[-n:][::-1]
        out[str(cls)] = [
            {"token": feature_names[j], "weight": float(weights[j])} for j in top_idx
        ]
    return out


def run(
    processed_dir: Path | str = "data/processed",
    vectorizer_path: Path | str = "artifacts/vectorizer.joblib",
    metrics_out: Path | str = TRAIN_METRICS_OUT,
    uri_out: Path | str = MODEL_URI_OUT,
    config_path: Path | str = "params.yaml",
    tracking_uri: str | None = None,
) -> dict[str, Any]:
    cfg = TrainingConfig.from_file(config_path)
    configure_mlflow(tracking_uri)

    processed = Path(processed_dir)
    train_df = pd.read_parquet(processed / "train.parquet")
    val_df = pd.read_parquet(processed / "val.parquet")

    featurizer = TextFeaturizer.load(vectorizer_path)
    X_train = featurizer.transform(train_df["text"].tolist())
    y_train = train_df["label"].astype(str).to_numpy()
    X_val = featurizer.transform(val_df["text"].tolist())
    y_val = val_df["label"].astype(str).to_numpy()

    clf = _build_classifier(cfg)
    t0 = time.perf_counter()
    clf.fit(X_train, y_train)
    train_seconds = round(time.perf_counter() - t0, 4)

    y_val_pred = clf.predict(X_val)
    y_val_proba = clf.predict_proba(X_val)
    val_metrics = classification_metrics(y_val, y_val_pred, y_val_proba)

    with mlflow_run(
        run_name=f"{cfg.model_type}-train",
        tags={
            "phase": "4",
            "model_type": cfg.model_type,
            "model_package_version": model_pkg_version,
            "feature_package_version": featurizer.feature_package_version_,
        },
    ) as run:
        # Core params + metrics
        mlflow.log_params(
            {
                "model_type": cfg.model_type,
                "class_weight": cfg.class_weight,
                "C": cfg.C,
                "max_iter": cfg.max_iter,
                "random_seed": cfg.random_seed,
                "train_size": len(train_df),
                "val_size": len(val_df),
                "vocab_size": featurizer.vocab_size_,
            }
        )
        mlflow.log_metrics(
            {
                "train_seconds": train_seconds,
                "val_accuracy": val_metrics["accuracy"],
                "val_macro_f1": val_metrics["macro_f1"],
                "val_weighted_f1": val_metrics["weighted_f1"],
                **{
                    f"val_{lbl}_f1": val_metrics["per_class"][lbl]["f1"]
                    for lbl in val_metrics["per_class"]
                },
                **(
                    {"val_log_loss": val_metrics["log_loss"]}
                    if "log_loss" in val_metrics
                    else {}
                ),
            }
        )

        # Artifacts: confusion matrix, classification report, feature metadata,
        # top features per class, sample predictions
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            render_confusion_matrix(y_val, y_val_pred, tdp / "confusion_matrix_val.png")
            (tdp / "classification_report_val.txt").write_text(
                val_metrics["classification_report"], encoding="utf-8"
            )
            (tdp / "feature_metadata.json").write_text(
                json.dumps(featurizer.metadata(), indent=2), encoding="utf-8"
            )
            (tdp / "top_features.json").write_text(
                json.dumps(
                    _top_feature_importances(clf, featurizer.feature_names()),
                    indent=2,
                ),
                encoding="utf-8",
            )
            sample = val_df.head(20).copy()
            sample["prediction"] = y_val_pred[: len(sample)]
            sample[["ticker", "text", "label", "prediction"]].to_csv(
                tdp / "sample_predictions.csv", index=False
            )
            for f in tdp.iterdir():
                mlflow.log_artifact(str(f))

        # Bundle the vectorizer alongside the classifier so serving never
        # has to know about the Phase 3 package internals. The loader
        # (Phase 5) unpickles this file and has both components.
        bundle_path = Path(tempfile.mkdtemp()) / "bundle.joblib"
        import joblib

        joblib.dump({"vectorizer": featurizer, "classifier": clf}, bundle_path)
        mlflow.log_artifact(str(bundle_path), artifact_path="bundle")

        # Log the sklearn classifier via mlflow.sklearn for models-serve.
        # The signature is inferred from the transformed val set; the live
        # serving path wraps raw text -> transform -> predict in Phase 5.
        mlflow.sklearn.log_model(
            clf,
            artifact_path="model",
            registered_model_name=cfg.registry_name,
        )
        model_uri = f"runs:/{run.info.run_id}/model"
        logger.info(
            "training_done",
            run_id=run.info.run_id,
            val_macro_f1=val_metrics["macro_f1"],
            vocab_size=featurizer.vocab_size_,
        )

    # DVC-tracked outputs
    out_payload = {
        "run_id": run.info.run_id,
        "model_uri": model_uri,
        "train_seconds": train_seconds,
        "val_metrics": val_metrics,
        "model_package_version": model_pkg_version,
        "feature_package_version": featurizer.feature_package_version_,
    }
    Path(metrics_out).parent.mkdir(parents=True, exist_ok=True)
    Path(metrics_out).write_text(json.dumps(out_payload, indent=2), encoding="utf-8")
    Path(uri_out).write_text(model_uri + "\n", encoding="utf-8")
    return out_payload


def _cli() -> None:
    p = argparse.ArgumentParser(description="Train the sentiment classifier.")
    p.add_argument("--processed-dir", default="data/processed")
    p.add_argument("--vectorizer", default="artifacts/vectorizer.joblib")
    p.add_argument("--metrics", default=str(TRAIN_METRICS_OUT))
    p.add_argument("--uri-out", default=str(MODEL_URI_OUT))
    p.add_argument("--config", default="params.yaml")
    p.add_argument("--tracking-uri", default=None)
    args = p.parse_args()
    run(
        args.processed_dir,
        args.vectorizer,
        args.metrics,
        args.uri_out,
        args.config,
        args.tracking_uri,
    )


if __name__ == "__main__":
    _cli()
