"""MLflow Model Registry helpers.

Encapsulates promotion and rollback so Phase 5/6/9 can reuse the same
logic. The evaluate stage decides the transitions; this module just
performs them deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass

import mlflow
import structlog
from mlflow.tracking import MlflowClient

logger = structlog.get_logger()

STAGING = "Staging"
PRODUCTION = "Production"
ARCHIVED = "Archived"


@dataclass
class Version:
    name: str
    version: str
    stage: str


def _client() -> MlflowClient:
    return MlflowClient(tracking_uri=mlflow.get_tracking_uri())


def latest_in_stage(name: str, stage: str) -> Version | None:
    """Latest version currently occupying `stage`, or None."""
    versions = _client().get_latest_versions(name, stages=[stage])
    if not versions:
        return None
    v = versions[0]
    return Version(name=v.name, version=v.version, stage=v.current_stage)


def transition(name: str, version: str, stage: str, archive_existing: bool = True) -> Version:
    """Move a version into `stage`, optionally archiving whoever was there."""
    cli = _client()
    mv = cli.transition_model_version_stage(
        name=name,
        version=version,
        stage=stage,
        archive_existing_versions=archive_existing,
    )
    logger.info("model_transitioned", name=name, version=version, stage=stage)
    return Version(name=mv.name, version=mv.version, stage=mv.current_stage)


def promote_if_better(
    name: str,
    candidate_version: str,
    candidate_metric: float,
    threshold_delta: float = 0.01,
) -> tuple[Version, bool]:
    """Promote candidate to Production if it beats the current Production by delta.

    Returns (version_after, was_promoted).
    """
    current = latest_in_stage(name, PRODUCTION)
    if current is None:
        # No incumbent — promote straight to Production
        v = transition(name, candidate_version, PRODUCTION)
        return v, True

    cli = _client()
    # Compare on macro_f1 stored as a run metric via train.py
    current_run = cli.get_model_version(name, current.version)
    current_metric_val = None
    if current_run.run_id:
        run = cli.get_run(current_run.run_id)
        current_metric_val = run.data.metrics.get("val_macro_f1")
    if current_metric_val is None:
        # Can't compare; stay safe and leave current Production alone.
        logger.info(
            "promotion_skipped_no_baseline_metric",
            current_version=current.version,
        )
        return current, False

    if candidate_metric > current_metric_val + threshold_delta:
        v = transition(name, candidate_version, PRODUCTION)
        logger.info(
            "promoted",
            new=v.version,
            candidate_metric=candidate_metric,
            prev_metric=current_metric_val,
        )
        return v, True

    logger.info(
        "not_promoted",
        candidate_metric=candidate_metric,
        prev_metric=current_metric_val,
        threshold_delta=threshold_delta,
    )
    return current, False


def rollback(name: str, target_version: str) -> tuple[Version, Version]:
    """Swap Production with `target_version`, archiving the current Prod.

    Returns (previous_production, new_production).
    """
    previous = latest_in_stage(name, PRODUCTION)
    if previous and previous.version == target_version:
        raise ValueError(f"{target_version} is already Production")
    new_prod = transition(name, target_version, PRODUCTION)
    prev_out = previous or Version(name=name, version="", stage="")
    return prev_out, new_prod
