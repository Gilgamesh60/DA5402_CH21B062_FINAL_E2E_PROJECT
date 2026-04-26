"""Placeholder DAG so Airflow scheduler has something to parse in Phase 1.

Real DAGs (ingestion, retraining) land in Phase 2 and Phase 9.
"""

from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.empty import EmptyOperator

with DAG(
    dag_id="ssa_placeholder",
    description="Phase 1 placeholder",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["ssa", "phase1"],
) as dag:
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")
    start >> end
