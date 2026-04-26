"""Airflow DAG mirroring the DVC ingestion pipeline.

The repo is bind-mounted read-only at /opt/airflow/repo and PYTHONPATH
points at /opt/airflow/repo/src, so the DAG's PythonOperators can import
ssa_ingestion directly without a container rebuild.

Schedule is None in Phase 2 (manual trigger only); cron schedule gets
flipped on in Phase 9 once live data sources are configured.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

DEFAULT_ARGS = {
    "owner": "ssa",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
    "depends_on_past": False,
}

REPO = "/opt/airflow/repo"  # bind-mounted via docker-compose


def _run_ingest() -> None:
    import os

    os.chdir(REPO)
    from ssa_ingestion.pipeline import run as ingest_run

    ingest_run()


def _run_validate() -> None:
    import os

    os.chdir(REPO)
    from ssa_ingestion.validation import run as validate_run

    validate_run()


def _run_eda() -> None:
    import os

    os.chdir(REPO)
    from ssa_ingestion.eda import run as eda_run

    eda_run()


with DAG(
    dag_id="ssa_ingestion",
    description="Ingest → validate → EDA baseline generation",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["ssa", "phase2", "data"],
) as dag:

    ingest = PythonOperator(task_id="ingest", python_callable=_run_ingest)
    validate = PythonOperator(task_id="validate", python_callable=_run_validate)
    eda = PythonOperator(task_id="eda_baselines", python_callable=_run_eda)

    ingest >> validate >> eda
