# Test Report

Generated: **2026-04-27 18:54 UTC**

This report is machine-generated from `artifacts/junit.xml` and `artifacts/acceptance_report.json`. Regenerate with `make test-report`.

## Summary

| Metric | Count |
|---|---:|
| Total tests | 78 |
| Passed | 78 |
| Failed | 0 |
| Errored | 0 |
| Skipped | 0 |
| Pass rate | **100.0%** |

## Results by file

| File | Total | Passed | Failed | Errored | Skipped |
|---|---:|---:|---:|---:|---:|
| `tests/contract/test_api_contract` | 13 | 13 | 0 | 0 | 0 |
| `tests/e2e/test_happy_path` | 11 | 11 | 0 | 0 | 0 |
| `tests/integration/test_compose_config` | 2 | 2 | 0 | 0 | 0 |
| `tests/unit/test_api_health` | 5 | 5 | 0 | 0 | 0 |
| `tests/unit/test_api_inference` | 5 | 5 | 0 | 0 | 0 |
| `tests/unit/test_features_cleaning` | 9 | 9 | 0 | 0 | 0 |
| `tests/unit/test_features_vectorizer` | 6 | 6 | 0 | 0 | 0 |
| `tests/unit/test_feedback_metrics` | 2 | 2 | 0 | 0 | 0 |
| `tests/unit/test_ingestion_pipeline` | 3 | 3 | 0 | 0 | 0 |
| `tests/unit/test_ingestion_schemas` | 6 | 6 | 0 | 0 | 0 |
| `tests/unit/test_model_metrics` | 4 | 4 | 0 | 0 | 0 |
| `tests/unit/test_model_reproducibility` | 5 | 5 | 0 | 0 | 0 |
| `tests/unit/test_monitoring_drift` | 7 | 7 | 0 | 0 | 0 |

## Acceptance criteria

Generated: 2026-04-27T18:53:59.821576+00:00

**Overall: PASS**

| Criterion | Target | Actual | Status |
|---|---|---|---|
| predict_p95_latency | 200 | 192.9 | ✅ PASS |
| predict_error_rate | 5.0 | 0.0 | ✅ PASS |
| ready_within_timeout | 30 | reached | ✅ PASS |
| model_macro_f1 | 0.75 | 1.0 | ✅ PASS |

### Raw /predict timings

- requests: 30, successful: 30, errors: 0
- p50: 37.2ms, p95: 192.9ms, mean: 52.3ms

## Links

- [Test plan](test-plan.md)
- [Acceptance criteria](acceptance-criteria.md)
- [Phase log](phase-log.md)
