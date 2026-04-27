"""Airflow DAG that aggregates feedback into Prometheus metrics.

Schedule: hourly. Reads from the predictions + feedback tables in
Postgres, computes agreement rate and per-version accuracy, writes a
Prometheus text file the drift-exporter serves.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

REPO = "/opt/airflow/repo"

DEFAULT_ARGS = {
    "owner": "ssa",
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}


def _run_feedback_aggregation() -> None:
    import os

    os.chdir(REPO)
    os.environ.setdefault("POSTGRES_HOST", "postgres")
    os.environ.setdefault("POSTGRES_PORT", "5432")
    os.environ.setdefault("POSTGRES_USER", "mlops")
    os.environ.setdefault("POSTGRES_PASSWORD", "mlops_local_dev")
    os.environ.setdefault("POSTGRES_DB", "mlops")

    from ssa_monitoring.feedback_metrics import run as feedback_run

    feedback_run()


with DAG(
    dag_id="ssa_feedback_metrics",
    description="Aggregate /feedback into Prometheus metrics",
    schedule=timedelta(hours=1),
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["ssa", "phase9", "monitoring"],
) as dag:

    aggregate = PythonOperator(
        task_id="aggregate_feedback", python_callable=_run_feedback_aggregation
    )
