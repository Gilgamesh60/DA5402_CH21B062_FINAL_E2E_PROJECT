"""Evaluate the trained model on the holdout test split and decide promotion.

Reads the run id from `artifacts/model_uri.txt`, pulls metrics against
the test set, and — if it beats the current Production by the
configured delta — promotes to Production. Emits a decision report DVC
tracks as a metric.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import mlflow
import pandas as pd
import structlog
import yaml

from ssa_model.metrics import classification_metrics, render_confusion_matrix
from ssa_model.registry import STAGING, promote_if_better, transition
from ssa_model.tracking import configure_mlflow

logger = structlog.get_logger()

EVAL_METRICS_OUT = Path("artifacts/eval_metrics.json")
DECISION_OUT = Path("artifacts/promotion_decision.json")


@dataclass
class EvalConfig:
    primary_metric: str = "macro_f1"
    acceptance_threshold: float = 0.75
    promote_on_improvement: bool = True
    staging_threshold_delta: float = 0.01
    registry_name: str = "stock-sentiment"

    @classmethod
    def from_file(cls, path: Path | str = "params.yaml") -> "EvalConfig":
        with Path(path).open("r", encoding="utf-8") as fh:
            raw: dict[str, Any] = yaml.safe_load(fh)
        ev = raw.get("evaluation", {})
        reg = raw.get("registry", {})
        return cls(
            primary_metric=str(ev.get("primary_metric", "macro_f1")),
            acceptance_threshold=float(ev.get("acceptance_threshold", 0.75)),
            promote_on_improvement=bool(reg.get("promote_on_improvement", True)),
            staging_threshold_delta=float(reg.get("staging_threshold_delta", 0.01)),
            registry_name=str(reg.get("model_name", "stock-sentiment")),
        )


def _load_bundle_for_run(run_id: str) -> dict[str, Any]:
    """Download the (vectorizer, classifier) bundle logged by train.py."""
    local = mlflow.artifacts.download_artifacts(
        run_id=run_id, artifact_path="bundle/bundle.joblib"
    )
    return joblib.load(local)


def run(
    processed_dir: Path | str = "data/processed",
    uri_path: Path | str = "artifacts/model_uri.txt",
    metrics_out: Path | str = EVAL_METRICS_OUT,
    decision_out: Path | str = DECISION_OUT,
    config_path: Path | str = "params.yaml",
    tracking_uri: str | None = None,
) -> dict[str, Any]:
    cfg = EvalConfig.from_file(config_path)
    configure_mlflow(tracking_uri)

    uri = Path(uri_path).read_text(encoding="utf-8").strip()
    run_id = uri.split("runs:/")[1].split("/")[0]
    client = mlflow.tracking.MlflowClient()
    bundle = _load_bundle_for_run(run_id)
    featurizer = bundle["vectorizer"]
    clf = bundle["classifier"]

    test_df = pd.read_parquet(Path(processed_dir) / "test.parquet")
    X_test = featurizer.transform(test_df["text"].tolist())
    y_test = test_df["label"].astype(str).to_numpy()
    y_pred = clf.predict(X_test)
    y_proba = clf.predict_proba(X_test)
    test_metrics = classification_metrics(y_test, y_pred, y_proba)

    primary_value = test_metrics[cfg.primary_metric]
    passed_acceptance = primary_value >= cfg.acceptance_threshold

    # Log test-set metrics + artifacts against the same run
    with mlflow.start_run(run_id=run_id):
        mlflow.log_metrics(
            {
                "test_accuracy": test_metrics["accuracy"],
                "test_macro_f1": test_metrics["macro_f1"],
                "test_weighted_f1": test_metrics["weighted_f1"],
                **{
                    f"test_{lbl}_f1": test_metrics["per_class"][lbl]["f1"]
                    for lbl in test_metrics["per_class"]
                },
            }
        )
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            render_confusion_matrix(y_test, y_pred, tdp / "confusion_matrix_test.png")
            (tdp / "classification_report_test.txt").write_text(
                test_metrics["classification_report"], encoding="utf-8"
            )
            (tdp / "test_summary.json").write_text(
                json.dumps(test_metrics, indent=2), encoding="utf-8"
            )
            for f in tdp.iterdir():
                mlflow.log_artifact(str(f))

    # Promotion decision
    model_versions = client.search_model_versions(f"name='{cfg.registry_name}'")
    this_version = next(
        (v.version for v in model_versions if v.run_id == run_id), None
    )
    decision = {
        "run_id": run_id,
        "registered_version": this_version,
        "primary_metric": cfg.primary_metric,
        "primary_value": primary_value,
        "acceptance_threshold": cfg.acceptance_threshold,
        "passed_acceptance": passed_acceptance,
        "promoted_to_production": False,
        "promoted_to_staging": False,
        "reason": None,
    }

    if this_version is None:
        decision["reason"] = "version-not-found-in-registry"
    elif not passed_acceptance:
        decision["reason"] = (
            f"below acceptance threshold "
            f"({primary_value:.4f} < {cfg.acceptance_threshold:.4f})"
        )
        # Park below-threshold runs in Staging so the history is visible.
        transition(cfg.registry_name, this_version, STAGING, archive_existing=False)
        decision["promoted_to_staging"] = True
    else:
        transition(cfg.registry_name, this_version, STAGING, archive_existing=False)
        decision["promoted_to_staging"] = True
        if cfg.promote_on_improvement:
            version_after, was_promoted = promote_if_better(
                cfg.registry_name,
                this_version,
                primary_value,
                cfg.staging_threshold_delta,
            )
            decision["promoted_to_production"] = was_promoted
            decision["reason"] = (
                "promoted"
                if was_promoted
                else "kept in Staging — no improvement over current Production"
            )
        else:
            decision["reason"] = "promotion disabled in params.yaml"

    Path(metrics_out).parent.mkdir(parents=True, exist_ok=True)
    Path(metrics_out).write_text(json.dumps(test_metrics, indent=2), encoding="utf-8")
    Path(decision_out).write_text(json.dumps(decision, indent=2), encoding="utf-8")
    logger.info(
        "evaluation_done",
        test_macro_f1=test_metrics["macro_f1"],
        passed=passed_acceptance,
        promoted=decision["promoted_to_production"],
    )
    return {"metrics": test_metrics, "decision": decision}


def _cli() -> None:
    p = argparse.ArgumentParser(description="Evaluate + decide promotion.")
    p.add_argument("--processed-dir", default="data/processed")
    p.add_argument("--uri-path", default="artifacts/model_uri.txt")
    p.add_argument("--metrics", default=str(EVAL_METRICS_OUT))
    p.add_argument("--decision", default=str(DECISION_OUT))
    p.add_argument("--config", default="params.yaml")
    p.add_argument("--tracking-uri", default=None)
    args = p.parse_args()
    run(
        args.processed_dir,
        args.uri_path,
        args.metrics,
        args.decision,
        args.config,
        args.tracking_uri,
    )


if __name__ == "__main__":
    _cli()
