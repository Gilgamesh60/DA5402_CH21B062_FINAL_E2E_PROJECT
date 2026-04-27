"""Aggregate /feedback rows into real-world accuracy metrics.

Joins `feedback` to `predictions` and computes:
    feedback_total              Counter of submissions
    feedback_agreement_rate     Agreement between predicted + ground truth
    feedback_accuracy_by_model  Accuracy per model version
    feedback_last_run_timestamp Unix time of the last aggregation

Writes a Prometheus text file the drift-exporter serves alongside
drift_metrics.prom.
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import structlog

logger = structlog.get_logger()

DEFAULT_DSN = os.getenv(
    "POSTGRES_DSN",
    "postgresql://mlops:mlops_local_dev@postgres:5432/mlops",
)

OUTPUT = Path("artifacts/feedback_metrics.prom")


def _dsn_from_env_or_compose_local() -> str:
    """Use POSTGRES_DSN if provided; otherwise assume local docker compose."""
    dsn = os.getenv("POSTGRES_DSN")
    if dsn:
        return dsn
    # From inside a container where postgres is reachable by service name
    if os.getenv("POSTGRES_HOST") == "postgres":
        return DEFAULT_DSN
    # From the host (running manually)
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER", "mlops")
    pw = os.getenv("POSTGRES_PASSWORD", "mlops_local_dev")
    db = os.getenv("POSTGRES_DB", "mlops")
    return f"postgresql://{user}:{pw}@{host}:{port}/{db}"


def aggregate(dsn: str | None = None) -> dict:
    dsn = dsn or _dsn_from_env_or_compose_local()
    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM feedback;")
            total = cur.fetchone()[0]

            cur.execute(
                """
                SELECT
                    AVG(CASE WHEN f.true_label = f.predicted_label THEN 1.0 ELSE 0.0 END)
                FROM feedback f
                WHERE f.predicted_label IS NOT NULL
                """
            )
            row = cur.fetchone()
            agreement = float(row[0]) if row and row[0] is not None else None

            cur.execute(
                """
                SELECT
                    p.model_version,
                    COUNT(*) AS n,
                    AVG(CASE WHEN f.true_label = p.predicted_label THEN 1.0 ELSE 0.0 END) AS acc
                FROM feedback f
                JOIN predictions p USING (prediction_request_id)
                GROUP BY p.model_version
                ORDER BY p.model_version
                """
            )
            per_version = [
                {"model_version": r[0], "n": int(r[1]), "accuracy": float(r[2])}
                for r in cur.fetchall()
            ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "feedback_total": int(total),
        "agreement_rate": agreement,
        "per_model_version": per_version,
    }


def render_prom(report: dict, out_path: Path | str = OUTPUT) -> Path:
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []

    lines.append("# HELP feedback_total Total feedback submissions")
    lines.append("# TYPE feedback_total gauge")
    lines.append(f"feedback_total {report['feedback_total']}")

    if report["agreement_rate"] is not None:
        lines.append(
            "# HELP feedback_agreement_rate Fraction of predictions user confirmed correct"
        )
        lines.append("# TYPE feedback_agreement_rate gauge")
        lines.append(f"feedback_agreement_rate {report['agreement_rate']}")

    if report["per_model_version"]:
        lines.append("# HELP feedback_accuracy_by_model Accuracy per model version from feedback")
        lines.append("# TYPE feedback_accuracy_by_model gauge")
        for row in report["per_model_version"]:
            lines.append(
                f'feedback_accuracy_by_model{{version="{row["model_version"]}"}} {row["accuracy"]}'
            )

    lines.append("# HELP feedback_last_run_timestamp Unix timestamp of the last feedback aggregation")
    lines.append("# TYPE feedback_last_run_timestamp gauge")
    lines.append(
        f"feedback_last_run_timestamp {int(datetime.fromisoformat(report['generated_at']).timestamp())}"
    )
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def run(dsn: str | None = None, out_path: Path | str = OUTPUT) -> dict:
    report = aggregate(dsn)
    render_prom(report, out_path)
    logger.info(
        "feedback_metrics_done",
        total=report["feedback_total"],
        agreement=report["agreement_rate"],
    )
    return report


def _cli() -> None:
    p = argparse.ArgumentParser(description="Aggregate feedback → Prometheus metrics.")
    p.add_argument("--dsn", default=None)
    p.add_argument("--out", default=str(OUTPUT))
    args = p.parse_args()
    run(args.dsn, args.out)


if __name__ == "__main__":
    _cli()
