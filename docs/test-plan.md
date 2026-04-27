# Test Plan

## 1. Scope

Covers functional correctness of the sentiment pipeline end-to-end, API contract conformance, monitoring behavior, and non-functional targets from `acceptance-criteria.md`.

## 2. Test levels

| Level | Tool | Scope | Location |
|---|---|---|---|
| Unit | pytest | Pure functions in every `ssa_*` package | `tests/unit/` |
| Integration | pytest + docker compose | Multi-service flows (ingest → features → train) | `tests/integration/` |
| Contract | pytest + schemathesis | API responses validated against OpenAPI | `tests/contract/` |
| End-to-end | bash + curl + docker | Full user-facing flow through the stack | `tests/e2e/` (Phase 11) |
| Frontend | vitest | React component tests | `frontend/tests/` |

## 3. Environments

| Environment | Purpose |
|---|---|
| Local dev | Developer iteration |
| CI | GitHub Actions matrix (3.10, 3.11) |
| Demo | Full `docker compose up` on a laptop |

## 4. Acceptance criteria link

Every item in `acceptance-criteria.md` has at least one corresponding test case in the matrix below.

## 5. Test case matrix

As of Phase 11, 78 tests across 4 levels. See `docs/test-report.md` for live pass/fail counts.

### 5.1 Unit tests (52 cases)

| File | Cases | Covers |
|---|---:|---|
| `test_api_health.py` | 5 | API probes, metrics exposition, request-id middleware, ticker validation |
| `test_api_inference.py` | 5 | Aggregation of per-record predictions into ticker-level sentiment |
| `test_features_cleaning.py` | 9 | Text cleaning edge cases: URLs, mentions, cashtags, unicode, whitespace |
| `test_features_vectorizer.py` | 6 | TF-IDF wrapper API: fit/transform/save/load, metadata, pipeline E2E |
| `test_feedback_metrics.py` | 2 | Prometheus text exposition for feedback aggregation |
| `test_ingestion_pipeline.py` | 3 | End-to-end seed → validate → EDA |
| `test_ingestion_schemas.py` | 6 | Pydantic schema: ticker upcase, UTC normalise, regex, bounds, extras |
| `test_model_metrics.py` | 4 | classification_metrics + confusion matrix rendering |
| `test_model_reproducibility.py` | 5 | git SHA, DVC hash, hardware fingerprint, full context artifact |
| `test_monitoring_drift.py` | 7 | KS + JSD drift detection, Prom exposition rendering |

### 5.2 Integration tests (2 cases)

| File | Cases | Covers |
|---|---:|---|
| `test_compose_config.py` | 2 | `docker compose config --quiet` valid, all 11 services present |

### 5.3 Contract tests (13 cases)

| Endpoint | Cases |
|---|---:|
| `/health`, `/ready` | 3 |
| `/metrics` | 1 |
| `/model/info`, `/model/versions` | 2 |
| `/predict` (happy, invalid, unknown, bounds) | 4 |
| `/batch_predict` | 1 |
| `/feedback` | 2 |

### 5.4 End-to-end tests (11 cases)

- Frontend serves the SPA + runtime config + API proxy
- Prediction roundtrips through nginx → api → model-server
- Feedback journey writes to Postgres
- MLflow, Airflow, Prometheus, Grafana, Alertmanager all reachable
- Prometheus' `api` scrape target is UP

## 6. Entry / exit criteria

### Entry
- Code committed on a branch
- Pre-commit hooks passing
- `dvc repro` clean

### Exit
- All tests green
- Coverage ≥ 80% on `src/`
- No mypy errors
- `docs/test-report.md` regenerated with pass/fail counts

## 7. Roles

Single-developer project — developer owns authoring, execution, and reporting.

## 8. Risks

- Flaky external APIs (NewsAPI, Reddit) → tests against a fixture dataset only
- Docker-in-CI resource limits → integration tests run on self-hosted runner if needed
- Non-determinism in model training → random seeds pinned in `params.yaml`

## 9. Deliverables

- This plan
- Test case matrix (this file)
- Test execution report (`docs/test-report.md`, Phase 11)
- Coverage badge
