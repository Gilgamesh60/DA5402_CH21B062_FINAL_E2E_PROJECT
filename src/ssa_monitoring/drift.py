"""Data drift detection against EDA baselines.

Compares live feature stats (text length, word count, categorical
distributions) against `artifacts/baselines.json` using Kolmogorov-Smirnov
for numeric features and Jensen-Shannon divergence for categorical ones.

Emits Prometheus metrics to a file the sidecar exporter serves:
    feature_drift_pvalue{feature=...}         Gauge (KS p-value; lower = more drift)
    feature_drift_jsd{feature=...}            Gauge (JS divergence; higher = more drift)
    prediction_class_ratio{label=...}         Gauge
    prediction_class_ratio_zscore{label=...}  Gauge
    drift_detected{type=...}                  Gauge (1/0)
    drift_last_run_timestamp                  Gauge (unix time)
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import structlog
from scipy.stats import ks_2samp

logger = structlog.get_logger()

DRIFT_METRICS_OUT = Path("artifacts/drift_metrics.prom")
DRIFT_REPORT_OUT = Path("artifacts/drift_report.json")


# ---------------------------------------------------------------------------
# Distance functions
# ---------------------------------------------------------------------------
def _js_divergence(p: dict[str, float], q: dict[str, float]) -> float:
    """Jensen-Shannon divergence between two discrete distributions."""
    keys = sorted(set(p) | set(q))
    pv = np.array([p.get(k, 1e-9) for k in keys], dtype=float)
    qv = np.array([q.get(k, 1e-9) for k in keys], dtype=float)
    pv = pv / pv.sum()
    qv = qv / qv.sum()
    m = 0.5 * (pv + qv)

    def kl(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.sum(np.where(a > 0, a * np.log(a / b), 0.0)))

    return 0.5 * (kl(pv, m) + kl(qv, m))


def _ks_pvalue_from_baseline(live: np.ndarray, baseline_stats: dict[str, float]) -> float:
    """Synthesise a KS reference from baseline stats (mean/std) when we
    only have summary stats, not the raw values. Treats the baseline as
    Normal(mean, std) for the test.
    """
    if not baseline_stats or baseline_stats.get("count", 0) == 0:
        return 1.0
    mean = baseline_stats["mean"]
    std = max(baseline_stats["std"], 1e-6)
    rng = np.random.default_rng(42)
    # Match live sample size for a fair comparison
    synthetic = rng.normal(loc=mean, scale=std, size=max(len(live), 30))
    stat, pvalue = ks_2samp(live, synthetic)
    return float(pvalue)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def compute_drift(
    live_df: pd.DataFrame,
    baselines: dict[str, Any],
    live_predictions: dict[str, int] | None = None,
    p_value_threshold: float = 0.05,
    jsd_threshold: float = 0.1,
) -> dict[str, Any]:
    """Return a dict describing drift signals + an overall verdict."""
    if live_df.empty:
        return {
            "status": "skipped",
            "reason": "empty_live_dataframe",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # Numeric features — KS test against synthetic baseline
    live_text_len = live_df["text"].astype(str).str.len().to_numpy(dtype=float)
    live_word_count = live_df["text"].astype(str).str.split().str.len().to_numpy(dtype=float)
    numeric = {
        "text_length_chars": _ks_pvalue_from_baseline(
            live_text_len, baselines["features"].get("text_length_chars", {})
        ),
        "word_count": _ks_pvalue_from_baseline(
            live_word_count, baselines["features"].get("word_count", {})
        ),
    }

    # Categorical distributions — JS divergence against baseline proportions
    categorical: dict[str, float] = {}
    for field in ("ticker", "source"):
        if field not in live_df.columns:
            continue
        live_counts = Counter(live_df[field].dropna().astype(str))
        total = sum(live_counts.values()) or 1
        live_dist = {k: v / total for k, v in live_counts.items()}
        baseline_dist = baselines["distributions"].get(field, {})
        if baseline_dist:
            categorical[field] = _js_divergence(live_dist, baseline_dist)

    # Prediction class ratio — if provided, compare against baseline label dist
    pred_ratios: dict[str, float] = {}
    pred_zscores: dict[str, float] = {}
    if live_predictions:
        total_preds = sum(live_predictions.values()) or 1
        ratios = {k: v / total_preds for k, v in live_predictions.items()}
        baseline_label_dist = baselines["distributions"].get("label", {})
        for lbl, ratio in ratios.items():
            pred_ratios[lbl] = round(float(ratio), 6)
            baseline_ratio = baseline_label_dist.get(lbl)
            if baseline_ratio:
                n = total_preds
                se = math.sqrt(baseline_ratio * (1 - baseline_ratio) / max(n, 1))
                pred_zscores[lbl] = round((ratio - baseline_ratio) / max(se, 1e-9), 4)

    any_num_drift = any(p < p_value_threshold for p in numeric.values())
    any_cat_drift = any(d > jsd_threshold for d in categorical.values())
    any_class_drift = any(abs(z) > 2.0 for z in pred_zscores.values())

    return {
        "status": "ok",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sample_size": int(len(live_df)),
        "numeric": {k: round(v, 6) for k, v in numeric.items()},
        "categorical": {k: round(v, 6) for k, v in categorical.items()},
        "prediction_ratios": pred_ratios,
        "prediction_zscores": pred_zscores,
        "thresholds": {
            "p_value": p_value_threshold,
            "jsd": jsd_threshold,
            "zscore": 2.0,
        },
        "drift_detected": {
            "numeric": any_num_drift,
            "categorical": any_cat_drift,
            "class_ratio": any_class_drift,
            "any": any(
                [any_num_drift, any_cat_drift, any_class_drift]
            ),
        },
    }


def write_prom_file(report: dict[str, Any], out_path: Path | str) -> Path:
    """Render the drift report as a Prometheus text-exposition file."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []

    def _emit(name: str, help_text: str, type_: str, samples: list[tuple[dict[str, str], float]]) -> None:
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} {type_}")
        for labels, value in samples:
            if labels:
                label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
                lines.append(f"{name}{{{label_str}}} {value}")
            else:
                lines.append(f"{name} {value}")

    if report.get("status") != "ok":
        lines.append("# drift_computation_skipped")
        lines.append(f"# reason: {report.get('reason', 'unknown')}")
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return out_path

    _emit(
        "feature_drift_pvalue",
        "KS-test p-value per numeric feature (lower = more drift)",
        "gauge",
        [({"feature": k}, v) for k, v in report["numeric"].items()],
    )
    _emit(
        "feature_drift_jsd",
        "Jensen-Shannon divergence per categorical feature (higher = more drift)",
        "gauge",
        [({"feature": k}, v) for k, v in report["categorical"].items()],
    )
    if report["prediction_ratios"]:
        _emit(
            "prediction_class_ratio",
            "Observed prediction ratio by class",
            "gauge",
            [({"label": k}, v) for k, v in report["prediction_ratios"].items()],
        )
    if report["prediction_zscores"]:
        _emit(
            "prediction_class_ratio_zscore",
            "Z-score of live prediction ratio vs EDA baseline",
            "gauge",
            [({"label": k}, v) for k, v in report["prediction_zscores"].items()],
        )
    _emit(
        "drift_detected",
        "1 if drift detected for this signal type, 0 otherwise",
        "gauge",
        [
            ({"type": k}, int(bool(v)))
            for k, v in report["drift_detected"].items()
        ],
    )
    _emit(
        "drift_last_run_timestamp",
        "Unix timestamp of the last drift computation",
        "gauge",
        [({}, int(datetime.fromisoformat(report["generated_at"]).timestamp()))],
    )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


def run(
    live_path: Path | str = "data/interim/validated.parquet",
    baselines_path: Path | str = "artifacts/baselines.json",
    report_out: Path | str = DRIFT_REPORT_OUT,
    prom_out: Path | str = DRIFT_METRICS_OUT,
    p_value_threshold: float = 0.05,
    jsd_threshold: float = 0.1,
) -> dict[str, Any]:
    baselines = json.loads(Path(baselines_path).read_text(encoding="utf-8"))
    df = pd.read_parquet(live_path)
    report = compute_drift(df, baselines, None, p_value_threshold, jsd_threshold)
    Path(report_out).parent.mkdir(parents=True, exist_ok=True)
    Path(report_out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_prom_file(report, prom_out)
    logger.info(
        "drift_done",
        drift_any=report.get("drift_detected", {}).get("any"),
        sample_size=report.get("sample_size"),
        report=str(report_out),
    )
    return report


def _cli() -> None:
    p = argparse.ArgumentParser(description="Run drift detection.")
    p.add_argument("--live", default="data/interim/validated.parquet")
    p.add_argument("--baselines", default="artifacts/baselines.json")
    p.add_argument("--report", default=str(DRIFT_REPORT_OUT))
    p.add_argument("--prom", default=str(DRIFT_METRICS_OUT))
    p.add_argument("--pvalue-threshold", type=float, default=0.05)
    p.add_argument("--jsd-threshold", type=float, default=0.1)
    args = p.parse_args()
    run(
        live_path=args.live,
        baselines_path=args.baselines,
        report_out=args.report,
        prom_out=args.prom,
        p_value_threshold=args.pvalue_threshold,
        jsd_threshold=args.jsd_threshold,
    )


if __name__ == "__main__":
    _cli()
