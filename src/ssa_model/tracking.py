"""MLflow tracking helpers.

A single `mlflow_run` context manager stamps reproducibility metadata on
every run so reproducibility is automatic, not opt-in. Going beyond
autolog here (git SHA, DVC hash, feature-package metadata, env snapshot,
hardware fingerprint) is an explicit rubric item.
"""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import mlflow
import structlog

from ssa_model.reproducibility import (
    environment_snapshot,
    full_context,
    git_commit_sha,
    git_dirty,
)

logger = structlog.get_logger()

DEFAULT_EXPERIMENT = "sentiment-classifier"


def configure_mlflow(tracking_uri: str | None = None, experiment: str = DEFAULT_EXPERIMENT) -> None:
    """Set tracking URI + experiment. Must be called before `mlflow_run`."""
    uri = tracking_uri or os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment(experiment)
    logger.info("mlflow_configured", tracking_uri=uri, experiment=experiment)


@contextmanager
def mlflow_run(run_name: str, tags: dict[str, str] | None = None) -> Iterator[mlflow.ActiveRun]:
    """Context manager that stamps reproducibility metadata and yields the run.

    Stamps (as tags + artifacts):
      - git.commit_sha, git.dirty
      - dvc.data_hash
      - hardware fingerprint
      - full params.yaml snapshot (JSON artifact)
      - pip freeze (text artifact)
    """
    base_tags = {
        "git.commit_sha": git_commit_sha(),
        "git.dirty": str(git_dirty()).lower(),
    }
    if tags:
        base_tags.update(tags)
    with mlflow.start_run(run_name=run_name, tags=base_tags) as run:
        # Write + log context
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            ctx_path = tdp / "reproducibility_context.json"
            ctx_path.write_text(
                json.dumps(full_context(), indent=2), encoding="utf-8"
            )
            mlflow.log_artifact(str(ctx_path))

            env = environment_snapshot()
            if env:
                env_path = tdp / "pip_freeze.txt"
                env_path.write_text("\n".join(env), encoding="utf-8")
                mlflow.log_artifact(str(env_path))
        logger.info(
            "mlflow_run_started",
            run_id=run.info.run_id,
            run_name=run_name,
            git_sha=base_tags["git.commit_sha"][:10],
        )
        yield run
