"""Ingestion pipeline entry point.

Reads `params.yaml`, runs every enabled source, writes a parquet file
at `data/raw/records.parquet` plus an `IngestionReport` JSON.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import structlog

from ssa_ingestion.config import IngestionConfig
from ssa_ingestion.schemas import IngestionReport, TextRecord
from ssa_ingestion.sources import SeedSource

logger = structlog.get_logger()

RAW_OUTPUT = Path("data/raw/records.parquet")
REPORT_OUTPUT = Path("artifacts/ingestion_report.json")


def _build_sources(cfg: IngestionConfig) -> list:
    """Always include SeedSource; add live sources when keys are present."""
    out: list = [SeedSource()]
    if "newsapi" in cfg.news_sources:
        from ssa_ingestion.sources.newsapi import NewsApiSource

        out.append(NewsApiSource())
    if "reddit" in cfg.social_sources:
        from ssa_ingestion.sources.reddit import RedditSource

        out.append(RedditSource(subreddits=cfg.social_subreddits))
    return out


def run(
    config_path: Path | str = "params.yaml",
    output_path: Path | str = RAW_OUTPUT,
    report_path: Path | str = REPORT_OUTPUT,
) -> IngestionReport:
    started = datetime.now(timezone.utc)
    t0 = time.perf_counter()
    cfg = IngestionConfig.from_file(config_path)
    sources = _build_sources(cfg)

    records: list[TextRecord] = []
    per_source: dict[str, int] = {}
    errors: list[str] = []

    for src in sources:
        got = 0
        try:
            for rec in src.fetch(
                tickers=cfg.tickers,
                lookback_hours=cfg.news_lookback_hours,
                max_items=cfg.news_max_items_per_source,
            ):
                records.append(rec)
                got += 1
        except Exception as e:  # pragma: no cover — defence in depth
            msg = f"{src.name}: {e}"
            errors.append(msg)
            logger.error("source_failed", source=src.name, error=str(e))
        per_source[src.name] = got
        logger.info("source_done", source=src.name, count=got)

    df = pd.DataFrame([r.model_dump(mode="json") for r in records])
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)

    elapsed = time.perf_counter() - t0
    report = IngestionReport(
        started_at=started,
        finished_at=datetime.now(timezone.utc),
        sources=per_source,
        total_records=len(records),
        duration_seconds=round(elapsed, 3),
        throughput_rps=round(len(records) / elapsed, 2) if elapsed > 0 else 0.0,
        errors=errors,
    )
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report.to_json(), indent=2), encoding="utf-8")
    logger.info(
        "ingestion_done",
        total=report.total_records,
        throughput_rps=report.throughput_rps,
        duration_s=report.duration_seconds,
        output=str(output_path),
    )
    return report


def _cli() -> None:
    p = argparse.ArgumentParser(description="Run the ingestion pipeline.")
    p.add_argument("--config", default="params.yaml")
    p.add_argument("--output", default=str(RAW_OUTPUT))
    p.add_argument("--report", default=str(REPORT_OUTPUT))
    args = p.parse_args()
    run(args.config, args.output, args.report)


if __name__ == "__main__":
    _cli()
