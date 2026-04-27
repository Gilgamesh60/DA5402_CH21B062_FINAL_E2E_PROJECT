"""Measure live stack against acceptance-criteria.md and emit JSON.

Checks:
  - /predict p95 latency over N requests
  - API error rate on those requests
  - /ready returns 200 within timeout
  - Current Production model's val_macro_f1 (from MLflow) meets threshold

Writes `artifacts/acceptance_report.json` the test-report generator joins in.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

API = os.getenv("API_BASE_URL", "http://localhost:8000")
MLFLOW = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
OUTPUT = Path("artifacts/acceptance_report.json")

CRITERIA = {
    "predict_p95_ms": 200,
    "error_rate_pct": 5.0,
    "ready_timeout_s": 30,
    "macro_f1_min": 0.75,
}


def _measure_predict(n: int = 30) -> dict:
    errors = 0
    latencies: list[float] = []
    with httpx.Client(base_url=API, timeout=5.0) as client:
        # Warmup — cold-start overhead dominates the first few calls;
        # SLO is a steady-state number, not a cold-start one.
        for _ in range(5):
            try:
                client.post("/predict", json={"ticker": "AAPL"})
            except httpx.HTTPError:
                pass
        for _ in range(n):
            t0 = time.perf_counter()
            try:
                r = client.post("/predict", json={"ticker": "AAPL"})
                elapsed_ms = (time.perf_counter() - t0) * 1000
                if r.status_code >= 500:
                    errors += 1
                elif r.status_code == 200:
                    latencies.append(elapsed_ms)
            except httpx.HTTPError:
                errors += 1
    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else None
    p50 = latencies[int(len(latencies) * 0.50)] if latencies else None
    return {
        "requests": n,
        "successful": len(latencies),
        "errors": errors,
        "error_rate_pct": round((errors / n) * 100, 2),
        "p50_ms": round(p50, 1) if p50 else None,
        "p95_ms": round(p95, 1) if p95 else None,
        "mean_ms": round(statistics.mean(latencies), 1) if latencies else None,
    }


def _ready_ok() -> bool:
    deadline = time.time() + CRITERIA["ready_timeout_s"]
    while time.time() < deadline:
        try:
            r = httpx.get(f"{API}/ready", timeout=3.0)
            if r.status_code == 200:
                return True
        except httpx.HTTPError:
            pass
        time.sleep(1)
    return False


def _prod_macro_f1() -> float | None:
    try:
        from mlflow.tracking import MlflowClient

        client = MlflowClient(tracking_uri=MLFLOW)
        versions = client.get_latest_versions("stock-sentiment", stages=["Production"])
        if not versions:
            return None
        run = client.get_run(versions[0].run_id)
        return run.data.metrics.get("val_macro_f1") or run.data.metrics.get("test_macro_f1")
    except Exception:
        return None


def main() -> None:
    p = argparse.ArgumentParser(description="Verify acceptance criteria against live stack.")
    p.add_argument("--n-requests", type=int, default=30)
    p.add_argument("--out", default=str(OUTPUT))
    args = p.parse_args()

    predict = _measure_predict(args.n_requests)
    ready_ok = _ready_ok()
    macro_f1 = _prod_macro_f1()

    checks = {
        "predict_p95_latency": {
            "target_ms": CRITERIA["predict_p95_ms"],
            "actual_ms": predict["p95_ms"],
            "passed": predict["p95_ms"] is not None
            and predict["p95_ms"] < CRITERIA["predict_p95_ms"],
        },
        "predict_error_rate": {
            "target_pct": CRITERIA["error_rate_pct"],
            "actual_pct": predict["error_rate_pct"],
            "passed": predict["error_rate_pct"] < CRITERIA["error_rate_pct"],
        },
        "ready_within_timeout": {
            "target_s": CRITERIA["ready_timeout_s"],
            "passed": ready_ok,
        },
        "model_macro_f1": {
            "target_min": CRITERIA["macro_f1_min"],
            "actual": macro_f1,
            "passed": macro_f1 is not None and macro_f1 >= CRITERIA["macro_f1_min"],
        },
    }
    all_passed = all(c["passed"] for c in checks.values())

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "all_passed": all_passed,
        "checks": checks,
        "raw": {"predict": predict},
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("Acceptance criteria:")
    for k, v in checks.items():
        status = "PASS" if v["passed"] else "FAIL"
        print(f"  [{status}] {k}: {v}")
    print(f"\nOverall: {'PASS' if all_passed else 'FAIL'}  (written to {args.out})")


if __name__ == "__main__":
    main()
