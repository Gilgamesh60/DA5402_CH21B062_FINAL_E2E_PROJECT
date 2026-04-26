"""Validation stage — re-runs schema checks, dedupes, and reports.

Idempotent: given the same raw parquet, produces the same validated
parquet + report. Fails loudly only when zero records survive.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd
import structlog

from ssa_ingestion.config import ValidationConfig
from ssa_ingestion.schemas import TextRecord, ValidationReport

logger = structlog.get_logger()

VALIDATED_OUTPUT = Path("data/interim/validated.parquet")
REPORT_OUTPUT = Path("artifacts/validation_report.json")


def run(
    input_path: Path | str = "data/raw/records.parquet",
    output_path: Path | str = VALIDATED_OUTPUT,
    report_path: Path | str = REPORT_OUTPUT,
    config_path: Path | str = "params.yaml",
) -> ValidationReport:
    cfg = ValidationConfig.from_file(config_path)
    df = pd.read_parquet(input_path)
    input_count = len(df)

    rows: list[TextRecord] = []
    dropped_schema = 0
    dropped_length = 0
    dropped_language = 0

    for row in df.to_dict(orient="records"):
        # Normalise NaNs to None so Pydantic doesn't choke on them
        row = {k: (None if pd.isna(v) else v) for k, v in row.items()}
        text = row.get("text") or ""
        if not (cfg.min_text_length <= len(text) <= cfg.max_text_length):
            dropped_length += 1
            continue
        lang = row.get("language") or "en"
        if cfg.allowed_languages and lang not in cfg.allowed_languages:
            dropped_language += 1
            continue
        try:
            rec = TextRecord(**row)
        except Exception as e:
            dropped_schema += 1
            logger.warning("validation_schema_fail", error=str(e))
            continue
        rows.append(rec)

    # Dedupe using the configured key tuple
    seen: set[tuple] = set()
    deduped: list[TextRecord] = []
    dropped_duplicates = 0
    for rec in rows:
        vals = tuple(getattr(rec, k) for k in cfg.dedupe_on)
        if vals in seen:
            dropped_duplicates += 1
            continue
        seen.add(vals)
        deduped.append(rec)

    per_ticker = dict(Counter(r.ticker for r in deduped))
    per_source = dict(Counter(r.source.value for r in deduped))

    out = pd.DataFrame([r.model_dump(mode="json") for r in deduped])
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(output_path, index=False)

    report = ValidationReport(
        input_count=input_count,
        output_count=len(deduped),
        dropped_schema_errors=dropped_schema,
        dropped_duplicates=dropped_duplicates,
        dropped_length=dropped_length,
        dropped_language=dropped_language,
        per_ticker=per_ticker,
        per_source=per_source,
    )
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    logger.info(
        "validation_done",
        input=input_count,
        output=len(deduped),
        dropped_schema=dropped_schema,
        dropped_dupes=dropped_duplicates,
        dropped_length=dropped_length,
        dropped_language=dropped_language,
    )
    if not report.passed():
        raise RuntimeError("validation produced zero records")
    return report


def _cli() -> None:
    p = argparse.ArgumentParser(description="Validate ingested records.")
    p.add_argument("--input", default="data/raw/records.parquet")
    p.add_argument("--output", default=str(VALIDATED_OUTPUT))
    p.add_argument("--report", default=str(REPORT_OUTPUT))
    p.add_argument("--config", default="params.yaml")
    args = p.parse_args()
    run(args.input, args.output, args.report, args.config)


if __name__ == "__main__":
    _cli()
