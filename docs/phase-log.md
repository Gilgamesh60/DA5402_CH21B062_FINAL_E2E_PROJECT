# Phase log

Running journal of what landed in each phase and any problems encountered.
This feeds `docs/problems-faced.md` for the viva.

## Phase 0 — Scaffolding & contracts — ✅ complete

Delivered:
- Repo skeleton with package split (`ssa_ingestion`, `ssa_features`, `ssa_model`, `ssa_api`, `ssa_monitoring`)
- Tooling: black, ruff, isort, mypy, pre-commit, pytest
- Docs: architecture, HLD, LLD, acceptance criteria, test plan, conventions, user manual stub
- Central configs: `params.yaml`, `.env.example`, `pyproject.toml`, `MLproject`
- Placeholder `dvc.yaml` and `docker-compose.yml`
- GitHub Actions CI stub

Problems faced: none yet.

## Phase 1 — Infrastructure skeleton — ✅ complete

Delivered:
- `docker-compose.yml` with 10 services on a shared network: postgres, mlflow, model-server, api, airflow-init/webserver/scheduler, prometheus, grafana, frontend
- Postgres init SQL creates `mlflow` / `airflow` databases and the `feedback` table
- MLflow Dockerfile runs tracking server with postgres backend store + local artifact volume
- API stub (`src/ssa_api/main.py`) exposes `/health`, `/ready`, `/metrics`, `/` with structlog JSON logs, Prometheus instrumentation, request-id middleware; `/ready` forwards to model-server
- Model-server stub mimics the MLflow `/invocations` contract so Phase 4 can swap in the real thing
- Frontend stub: nginx serving a status page that pings the API (proves loose coupling + proxy path)
- Prometheus scrape config for api, model-server, airflow; alert rules for 5% error rate + p95 latency + feature drift
- Grafana provisioned with Prometheus datasource + starter "API overview" dashboard
- Placeholder Airflow DAG so the scheduler parses cleanly
- DVC initialized with local remote
- `.env` with dev defaults, `Makefile` with common targets, unit tests green (4/4)

Problems faced:
- Had to provide a fallback `airflow-init` service with `service_completed_successfully` depends_on to avoid race on Airflow DB migration
- Initial pip install of `mypy` on Python 3.14 was slow; switched dev install to a targeted set of runtime deps for the Phase 1 unit tests
- Docker daemon wasn't running locally during scaffolding; stack was validated via `docker compose config --quiet` and unit tests only. First live boot happens when Docker Desktop is running.
- Switched from Docker Desktop to Colima for local runtime (user preference). Had to resize the VM from 2 CPU / 2 GiB to 4 CPU / 8 GiB via `colima stop && colima start --cpu 4 --memory 8 --disk 60` — the default was too small for the full stack.
- Frontend nginx healthcheck initially failed because BusyBox `wget` in alpine hits `localhost` via IPv6; switched to `127.0.0.1` explicitly.

Live boot verification (Colima, aarch64):
- All 9 containers up, 8 healthy (airflow-scheduler has no declared healthcheck by design)
- `GET /health` → `{"status":"alive"}` ✓
- `GET /ready` → `{"status":"ready"}` (proves inter-service API ↔ model-server) ✓
- `/metrics` exposes `http_requests_total` and `http_request_duration_seconds` ✓
- MLflow, Airflow, Prometheus, Grafana, Frontend all return 200 on their health endpoints ✓
- Prometheus actively scraping `api` and `prometheus` (model-server and airflow pending their proper exporters)
- Grafana dashboard `ssa-api-overview` provisioned and queryable
## Phase 2 — Data ingestion + EDA + baselines — ⏳ pending
## Phase 3 — Feature engineering package — ⏳ pending
## Phase 4 — MLflow + baseline training — ⏳ pending
## Phase 5 — FastAPI gateway + model server — ⏳ pending
## Phase 6 — Prometheus + Grafana + alerts — ⏳ pending
## Phase 7 — Frontend + pipeline viz screens — ⏳ pending
## Phase 8 — CI/CD + rollback — ⏳ pending
## Phase 9 — Feedback loop + retraining — ⏳ pending
## Phase 10 — FinBERT + quantization — ⏳ pending
## Phase 11 — Tests + report — ⏳ pending
## Phase 12 — Security hardening — ⏳ pending
## Phase 13 — Demo polish + viva prep — ⏳ pending
