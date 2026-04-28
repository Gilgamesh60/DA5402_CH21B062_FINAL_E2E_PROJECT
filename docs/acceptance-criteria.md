# Acceptance Criteria

The software is considered acceptable when **all** criteria below are met on a clean `docker compose up` from a fresh clone, using the seed dataset.

## 1. ML metrics

| Metric | Target | Measured by |
|---|---|---|
| macro-F1 on held-out test set | ≥ 0.75 | `src/ssa_model/evaluate.py` |
| Per-class F1 (positive, negative, neutral) | ≥ 0.65 each | evaluation report |
| Calibration error (ECE) | ≤ 0.10 | evaluation report |

## 2. Business / operational metrics

| Metric | Target | Measured by |
|---|---|---|
| `/predict` p95 latency, explanations off | < 200 ms | Prometheus |
| `/batch_predict` p95 latency, 10 tickers | < 800 ms | Prometheus |
| API error rate, 5-minute window | < 5 % | Prometheus |
| `/ready` returns 200 within 30 s of stack boot | ✓ | smoke test |

## 3. MLOps non-functional

| Requirement | Target |
|---|---|
| Every experiment reproducible from `(git_sha, mlflow_run_id)` | ✓ |
| DVC DAG covers ingest → validate → features → train → evaluate | ✓ |
| Feature package `ssa_features` versioned independently of `ssa_model` | ✓ |
| Prometheus scrapes all 8 services | ✓ |
| Grafana dashboards include API SLOs, pipeline status, drift, throughput | ✓ |
| Alert fires when error rate > 5% or feature drift p < 0.05 | ✓ |
| Rollback to previous registry version completes in < 60 s | ✓ |
| Frontend reads `VITE_API_BASE_URL` at runtime (no rebuild to re-point) | ✓ |

## 4. Documentation

| Artifact | Status |
|---|---|
| Architecture diagram with block explanation | ✓ `docs/architecture.md` |
| High-level design doc with rationale | ✓ `docs/HLD.md` |
| Low-level design doc with endpoint I/O | ✓ `docs/LLD.md` |
| Test plan and test cases | ✓ `docs/test-plan.md` |
| Test report with pass/fail counts | See docs/test-report.md |
| User manual for non-technical users | See docs/user-manual.md |

## 5. Demo acceptance

- Fresh clone → `docker compose up -d` → all services healthy within 2 minutes
- Frontend loads at `http://localhost:3000` with no console errors
- Submitting a ticker returns a prediction in < 500 ms end-to-end
- Pipeline viz screen shows live Airflow, MLflow, Grafana status
- Rollback button works live without service downtime

## 6. Sign-off

This document is the pass/fail yardstick for the test report.
