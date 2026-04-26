"""EDA & drift-baseline generation.

Consumes validated records and produces `artifacts/baselines.json` —
the reference statistics the monitoring stage uses for drift detection.
Also writes a human-readable markdown summary.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger()

BASELINES_OUTPUT = Path("artifacts/baselines.json")
EDA_MD_OUTPUT = Path("artifacts/eda_summary.md")


def _numeric_stats(series: pd.Series) -> dict[str, float]:
    """Mean / variance / quantiles for a numeric series."""
    s = series.dropna().astype(float)
    if len(s) == 0:
        return {}
    return {
        "count": int(len(s)),
        "mean": float(s.mean()),
        "std": float(s.std(ddof=1)) if len(s) > 1 else 0.0,
        "variance": float(s.var(ddof=1)) if len(s) > 1 else 0.0,
        "min": float(s.min()),
        "p25": float(np.quantile(s, 0.25)),
        "median": float(s.median()),
        "p75": float(np.quantile(s, 0.75)),
        "max": float(s.max()),
    }


def _categorical_distribution(series: pd.Series) -> dict[str, float]:
    """Return normalised class proportions rounded to 6dp."""
    counts = Counter(series.dropna().astype(str))
    total = sum(counts.values()) or 1
    return {k: round(v / total, 6) for k, v in counts.items()}


def compute_baselines(df: pd.DataFrame) -> dict[str, Any]:
    """Build the baselines dict used by Phase 6 drift detection."""
    text_lengths = df["text"].astype(str).str.len()
    word_counts = df["text"].astype(str).str.split().str.len()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sample_size": int(len(df)),
        "features": {
            "text_length_chars": _numeric_stats(text_lengths),
            "word_count": _numeric_stats(word_counts),
        },
        "distributions": {
            "ticker": _categorical_distribution(df["ticker"]),
            "source": _categorical_distribution(df["source"]),
            "label": _categorical_distribution(df["label"]) if "label" in df else {},
        },
    }


def _render_markdown(baselines: dict[str, Any], df: pd.DataFrame) -> str:
    lines = [
        "# EDA summary",
        "",
        f"Generated: {baselines['generated_at']}",
        f"Sample size: {baselines['sample_size']}",
        "",
        "## Numeric features",
        "",
        "| Feature | mean | std | min | median | max |",
        "|---|---|---|---|---|---|",
    ]
    for name, stats in baselines["features"].items():
        if not stats:
            continue
        lines.append(
            f"| {name} | {stats['mean']:.2f} | {stats['std']:.2f} | "
            f"{stats['min']:.0f} | {stats['median']:.0f} | {stats['max']:.0f} |"
        )
    lines.extend(["", "## Class balance", ""])
    for k, v in baselines["distributions"].get("label", {}).items():
        lines.append(f"- **{k}**: {v:.2%}")
    lines.extend(["", "## Per-ticker volume", ""])
    for k, v in sorted(baselines["distributions"]["ticker"].items()):
        lines.append(f"- {k}: {int(v * baselines['sample_size'])}")
    lines.extend(["", "## Per-source volume", ""])
    for k, v in sorted(baselines["distributions"]["source"].items()):
        lines.append(f"- {k}: {int(v * baselines['sample_size'])}")

    # Missing values quick-check for the viva
    missing_pct = {c: round(df[c].isna().mean() * 100, 2) for c in df.columns}
    lines.extend(["", "## Missing values (%)", ""])
    for k, v in missing_pct.items():
        lines.append(f"- {k}: {v}%")
    return "\n".join(lines) + "\n"


def run(
    input_path: Path | str = "data/interim/validated.parquet",
    baselines_path: Path | str = BASELINES_OUTPUT,
    md_path: Path | str = EDA_MD_OUTPUT,
) -> dict[str, Any]:
    df = pd.read_parquet(input_path)
    if df.empty:
        raise RuntimeError("eda called on empty dataframe")
    baselines = compute_baselines(df)
    Path(baselines_path).parent.mkdir(parents=True, exist_ok=True)
    Path(baselines_path).write_text(json.dumps(baselines, indent=2), encoding="utf-8")
    Path(md_path).write_text(_render_markdown(baselines, df), encoding="utf-8")
    logger.info(
        "eda_done",
        sample_size=baselines["sample_size"],
        baselines=str(baselines_path),
    )
    return baselines


def _cli() -> None:
    p = argparse.ArgumentParser(description="Compute EDA drift baselines.")
    p.add_argument("--input", default="data/interim/validated.parquet")
    p.add_argument("--baselines", default=str(BASELINES_OUTPUT))
    p.add_argument("--summary", default=str(EDA_MD_OUTPUT))
    args = p.parse_args()
    run(args.input, args.baselines, args.summary)


if __name__ == "__main__":
    _cli()
