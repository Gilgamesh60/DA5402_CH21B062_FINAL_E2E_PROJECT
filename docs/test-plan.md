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

## 5. Test case matrix (initial)

| ID | Level | Description | Expected | AC link |
|---|---|---|---|---|
| U-001 | Unit | `ssa_features.clean_text` removes URLs | URL stripped | 1.1 |
| U-002 | Unit | `ssa_features.clean_text` preserves tickers | `$AAPL` kept | 1.1 |
| U-003 | Unit | `ssa_ingestion.validate` rejects text shorter than min | ValidationError | 3.1 |
| U-004 | Unit | `ssa_ingestion.validate` dedupes on (id, source) | duplicates removed | 3.1 |
| U-005 | Unit | `ssa_model.train` logs git SHA to MLflow | tag present | 3.1 |
| U-006 | Unit | `ssa_monitoring.drift.compute_drift` returns p-values | dict per feature | 3.1 |
| I-001 | Integration | DVC `repro` produces baselines.json | file exists, valid JSON | 1.1 |
| I-002 | Integration | Training run registers a new model version | registry count +1 | 3.1 |
| I-003 | Integration | Rollback transitions stages and reloads server | /model/info shows old version | 2.4 |
| C-001 | Contract | `/predict` 200 response matches OpenAPI schema | no schema errors | 1.1 |
| C-002 | Contract | `/predict` rejects invalid ticker with 400 + `INVALID_TICKER` | code matches | 1.1 |
| C-003 | Contract | `/health` returns 200 `{status:"alive"}` | body matches | 2.4 |
| C-004 | Contract | `/ready` returns 503 when model-server down | body matches | 2.4 |
| C-005 | Contract | `/feedback` writes row to postgres | row visible | 3.1 |
| C-006 | Contract | `/metrics` exposes `http_request_duration_seconds` | metric present | 3.1 |
| E-001 | E2E | Fresh stack boot → `/ready` 200 within 30 s | timing met | 2.4 |
| E-002 | E2E | Frontend predict flow returns sentiment | UI renders result | 5 |
| E-003 | E2E | Triggering drift alert starts retraining DAG | Airflow run appears | 3.1 |
| F-001 | Frontend | Ticker input rejects empty string | validation error shown | 1.1 |
| F-002 | Frontend | API error produces toast not a crash | toast visible | 1.1 |

Matrix grows as phases land.

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
