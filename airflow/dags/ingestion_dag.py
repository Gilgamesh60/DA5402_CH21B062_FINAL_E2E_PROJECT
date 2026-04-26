"""Airflow DAG mirroring the DVC ingestion pipeline.

Uses BashOperator to invoke the same entry points DVC uses, so one
codepath serves both ad-hoc `dvc repro` and scheduled runs. In Phase 2
the DAG runs only on manual trigger; scheduling is enabled once live
sources are configured in Phase 9.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

DEFAULT_ARGS = {
    "owner": "ssa",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
    "depends_on_past": False,
}

# Commands assume the DAG runs from the repo root. In production this is
# enforced by the container working directory; locally Airflow runs against
# the mounted /opt/airflow/dags, so we `cd /repo` via an env var set by
# compose in Phase 9. For Phase 2 we run the stages via DVC so output
# placement matches the DAG.
REPO = "/opt/airflow/repo"  # bind-mounted in Phase 9

with DAG(
    dag_id="ssa_ingestion",
    description="Ingest → validate → EDA baseline generation",
    schedule=None,  # manual trigger in Phase 2
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["ssa", "phase2", "data"],
) as dag:

    ingest = BashOperator(
        task_id="ingest",
        bash_command=f"cd {REPO} && python -m ssa_ingestion.pipeline",
    )

    validate = BashOperator(
        task_id="validate",
        bash_command=f"cd {REPO} && python -m ssa_ingestion.validation",
    )

    eda = BashOperator(
        task_id="eda_baselines",
        bash_command=f"cd {REPO} && python -m ssa_ingestion.eda",
    )

    ingest >> validate >> eda
