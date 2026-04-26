"""Airflow DAG that runs drift detection and writes the Prometheus file.

Schedule: every 30 minutes. The job reads the latest validated parquet,
compares it to EDA baselines, writes both a JSON report and a
Prometheus text-exposition file that the drift-exporter serves.
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


def _run_drift() -> None:
    import os

    os.chdir(REPO)
    from ssa_monitoring.drift import run as drift_run

    drift_run()


with DAG(
    dag_id="ssa_drift_detection",
    description="Compare live features to EDA baselines, emit Prometheus metrics",
    schedule=timedelta(minutes=30),
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["ssa", "phase6", "monitoring"],
) as dag:

    drift = PythonOperator(task_id="detect_drift", python_callable=_run_drift)
