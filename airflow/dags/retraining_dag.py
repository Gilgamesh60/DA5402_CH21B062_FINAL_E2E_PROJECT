"""Retraining DAG — runs the features → train → evaluate stages.

Triggers:
  - Manual (default) from the Airflow UI for demos
  - Webhook from Alertmanager when drift fires (wired in Phase 9 via
    Airflow's REST API; see the README for the cURL invocation)

The DAG reuses the DVC-repro'd datasets so it stays aligned with the
ad-hoc pipeline path. Evaluate decides promotion — no manual gate.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

REPO = "/opt/airflow/repo"

DEFAULT_ARGS = {
    "owner": "ssa",
    "retries": 0,
    "retry_delay": timedelta(minutes=2),
}


def _shared_setup() -> None:
    import os

    os.chdir(REPO)
    # MLflow inside compose
    os.environ.setdefault("MLFLOW_TRACKING_URI", "http://mlflow:5000")


def _refresh_features() -> None:
    _shared_setup()
    from ssa_features.pipeline import run as features_run

    features_run()


def _train() -> None:
    _shared_setup()
    from ssa_model.train import run as train_run

    train_run()


def _evaluate() -> None:
    _shared_setup()
    from ssa_model.evaluate import run as evaluate_run

    evaluate_run()


with DAG(
    dag_id="ssa_retraining",
    description="Refresh features → train → evaluate → (auto) promote",
    schedule=None,  # manual or webhook-triggered
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["ssa", "phase9", "training"],
    max_active_runs=1,
) as dag:

    features = PythonOperator(task_id="refresh_features", python_callable=_refresh_features)
    train = PythonOperator(task_id="train", python_callable=_train)
    evaluate = PythonOperator(task_id="evaluate", python_callable=_evaluate)

    features >> train >> evaluate
