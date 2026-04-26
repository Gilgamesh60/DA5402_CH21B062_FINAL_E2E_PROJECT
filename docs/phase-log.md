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
## Phase 2 — Data ingestion + EDA + baselines — ✅ complete

Delivered:
- Unified `TextRecord` Pydantic schema normalising news + social into one shape
- Pluggable source adapters: `SeedSource` (always on), `NewsApiSource`, `RedditSource` (both opt-in via env vars)
- Seed corpus generator → 300 labelled records across 7 tickers, deterministic (`scripts/generate_seed_corpus.py`)
- `ssa_ingestion.pipeline` runs enabled sources, writes `data/raw/records.parquet` + `artifacts/ingestion_report.json` with duration + throughput
- `ssa_ingestion.validation` re-checks schema, dedupes on `(id, source)`, enforces length + language, emits `artifacts/validation_report.json`, raises on zero surviving records
- `ssa_ingestion.eda` computes drift baselines (mean/std/variance/quantiles on numeric features, normalised distributions for categoricals) → `artifacts/baselines.json` + human-readable `artifacts/eda_summary.md`
- `dvc.yaml` now has three real stages: `ingest → validate → eda_baselines`, all wired with params, deps, outs, and metrics
- `dvc repro` runs end-to-end cleanly; `dvc metrics show` surfaces throughput, record counts, per-ticker/per-source distributions
- DVC DAG exported to `docs/diagrams/dvc-dag.dot` for the pipeline viz screen
- Real Airflow DAG `ssa_ingestion` replaces the Phase 1 placeholder
- 13 unit tests passing (6 new schema tests + 3 new end-to-end pipeline tests)
- Performance numbers recorded in `docs/performance.md` (seed throughput ~3800–5800 rec/s)

Problems faced:
- `dvc repro` initially failed with "command not found: python" because DVC inherits the shell's PATH, and zsh on macOS doesn't alias `python` to `python3`. Fixed by switching the stage commands to `python3` and activating the venv before `dvc repro`.
- Pandas serialises NaN values from parquet where Python expected `None`; added an explicit NaN→None normalisation step in `validation.run()` before handing rows to Pydantic.
## Phase 3 — Feature engineering package — ✅ complete

Delivered:
- `ssa_features` package bumped to `0.2.0` — independent version stamped on every saved vectorizer so mismatches are detectable
- `ssa_features.cleaning` — deterministic, stateless text cleaner (URLs, mentions, cashtags, unicode normalisation, whitespace)
- `ssa_features.vectorizer.TextFeaturizer` — sklearn-compatible wrapper around TF-IDF with `fit/transform/fit_transform/save/load/metadata/feature_names`
- `ssa_features.pipeline` — entry point that reads validated records, stratified-splits train/val/test, fits on train only (no leakage), transforms all splits, saves cleaned parquet + fitted vectorizer + report
- `dvc.yaml` gains the real `features` stage with deps, params, outs (3 parquets + joblib), and metrics (feature report)
- DVC DAG now branches cleanly: `ingest → validate → {eda_baselines, features}`
- 28 unit tests passing (15 new across cleaning + vectorizer + pipeline), coverage 74%
- Live seed run: 300 labelled → 209/30/61 split, vocab 467, class balance preserved within 2%

Problems faced:
- `train_test_split` throws on tiny classes; added a fallback to non-stratified split when any class has < 2 samples. Not hit by the current seed corpus but future-proofs live runs.
- Initially put `text_clean` inside the vectorizer so serving could pass raw text, but the persisted splits then didn't carry the cleaned version. Moved cleaning to happen once in `pipeline.run()` and stored `text_clean` as a first-class column in the parquets so Phase 4 training, Phase 6 drift detection, and Phase 11 test fixtures all look at identical inputs.
## Phase 4 — MLflow + baseline training — ✅ complete

Delivered:
- `ssa_model` package with four modules: `reproducibility`, `metrics`, `tracking`, `train`, `evaluate`, `registry`
- `tracking.mlflow_run` context manager stamps git SHA, DVC data hash, params snapshot, pip freeze, and hardware fingerprint on every run — satisfies the "beyond autolog" rubric item
- Baseline Logistic Regression trains in under 0.02 s on the seed corpus
- Registry versioning: new versions start in Staging; promotion to Production requires beating the incumbent by `registry.staging_threshold_delta` (0.01 macro-F1 default)
- `evaluate` stage runs holdout test, decides promotion, writes `artifacts/promotion_decision.json`
- `dvc.yaml` now has all six real stages fully connected: `ingest → validate → {eda_baselines, features → train → evaluate}`
- Two live runs completed: v1 promoted to Production, v2 kept in Staging (no improvement)
- 9 new unit tests (reproducibility + metrics); full suite: 37 tests passing
- DVC DAG exported to `docs/diagrams/dvc-dag.dot`, ready for the pipeline viz screen

Problems faced:
- sklearn 1.7 removed the `multi_class` kwarg from `LogisticRegression`; dropped it from the builder.
- MLflow artifact writes failed with `OSError: Read-only file system: '/mlflow'`. Root cause: by default `mlflow server` sets each new experiment's `artifact_location` to the local filesystem path `/mlflow/artifacts/<id>`, which the client then tries to write to directly — but the client was on the host, not inside the container. Fix: start the server with `--default-artifact-root mlflow-artifacts:/` + `--artifacts-destination <container-path>` so clients receive proxy URIs and upload over HTTP.
- Wiped and recreated the `mlflow` Postgres database after the fix because existing experiments had the bad `artifact_location` baked in.
- Client (venv) was MLflow 3.11.1 while server was still 2.10.2 — client called endpoints the server didn't have. Pinned the server Dockerfile to `mlflow==3.11.1` to match.
- MLflow 3.x emits `FutureWarning` for `transition_model_version_stage` in favour of aliases, but the evaluation rubric explicitly expects stage-based promotion. Left the warnings in place; migration to aliases is a Phase-post-grading concern.
## Phase 5 — FastAPI gateway + real MLflow model server — ✅ complete

Delivered:
- `src/ssa_api/schemas.py` — Pydantic request/response models matching the LLD contract exactly
- `src/ssa_api/main.py` — 10 endpoints implementing the full LLD: `/health`, `/ready`, `/metrics`, `/model/info`, `/model/versions`, `/model/rollback`, `/predict`, `/batch_predict`, `/feedback`, plus `/` landing page
- `src/ssa_api/middleware.py` — request-id + metrics + structured logging middleware
- `src/ssa_api/inference.py` — per-record prediction + aggregation (averaged probs, argmax for ticker-level sentiment)
- `src/ssa_api/model_client.py` — HTTP client for the model-server's `/invocations`
- `src/ssa_api/repo.py` — Postgres feedback writer + parquet-backed record lookup
- `src/ssa_model/pyfunc_wrapper.py` — MLflow pyfunc bundling (vectorizer + classifier) so the model-server accepts raw text
- `docker/model-server/Dockerfile` — swapped from Phase 1 stub to real `mlflow models serve -m models:/stock-sentiment/Production`
- `docker/api/Dockerfile` — runtime deps including psycopg2, mlflow-skinny, pandas, pyarrow
- `docker-compose.yml` — `./data` bind-mount on api, tighter healthchecks, MLflow allowed-hosts updated for compose network
- 6 new unit tests for the inference aggregation + API validation; full suite: 43 tests passing

Live verification (Colima):
- `/predict AAPL` → returns ticker-level sentiment with per-class scores, sample size, model metadata, request id, latency ≈ 480ms on first call (cached afterwards)
- `/batch_predict [AAPL, MSFT, NVDA]` → 3 results in ~350ms total
- `/feedback` → row visible in Postgres `feedback` table
- `/model/info` → surfaces git SHA + MLflow run id for reproducibility
- `/metrics` → emits `predictions_total{sentiment=...}`, `model_version_info`, `feedback_received_total`
- `mlflow models serve` loads pyfunc v1 from registry, responds to `/invocations`

Problems faced:
- MLflow 3.x `--allowed-hosts` defense rejected container-name Host headers (`mlflow:5000` from model-server). Fixed by expanding allowed-hosts in the Dockerfile to include the service name plus Docker's default bridge subnets.
- sklearn version mismatch between training (1.8.0 in venv) and serving (1.7.2 initially in model-server image). The unpickled LogisticRegression referenced attributes only in 1.8. Aligned by pinning `scikit-learn==1.8.0` in the model-server image.
- MLflow pyfunc scoring server passes rows as numpy scalars/arrays, not Python strings. Rewrote `SentimentPipeline._coerce_to_texts` to handle DataFrames, numpy scalars, single-element arrays, and dict-wrapped inputs uniformly.
- Switched model registration from `mlflow.sklearn.log_model` to a `pyfunc` bundle so the model-server accepts text instead of sparse matrices — cleaner HTTP contract and matches the rubric's "MLflow API-ification" item.
## Phase 6 — Prometheus + Grafana + alerts + drift — ✅ complete

Delivered:
- `ssa_monitoring.drift` — drift detection comparing live features to `artifacts/baselines.json`:
  - KS test on numeric features (text length, word count) with synthetic baseline
  - Jensen-Shannon divergence on categorical (ticker, source)
  - Optional z-score on prediction class ratios
  - Emits both JSON report and Prometheus text-exposition file
- `drift-exporter` service — tiny Python HTTP server that serves `artifacts/drift_metrics.prom` at `/metrics:9101`
- Prometheus scrape config updated: `api` + `drift` + `prometheus` jobs, all reporting UP
- 7 alert rules live: `APIHighErrorRate` (> 5% for 2m), `APIHighLatencyP95` (> 200ms for 5m), `APIDown`, `FeatureDriftNumeric`, `FeatureDriftCategorical`, `PredictionClassRatioAnomaly`, `DriftJobStale`
- Second Grafana dashboard `Stock Sentiment — ML monitoring` with prediction distribution, model version stat, feedback rate, drift p-value + JSD timeseries, drift-detected stat, drift age
- Airflow DAG `ssa_drift_detection` scheduled every 30 minutes
- DVC stage `drift` branched off `validate + eda_baselines`, making the DAG 8 fully-connected stages
- 7 new unit tests; full suite: 50 tests passing

Live verification:
- `curl http://localhost:9101/metrics` returns the Prom exposition with 4 metric families
- Prometheus `/api/v1/targets` shows all 3 jobs UP
- `feature_drift_pvalue` and `feature_drift_jsd` queryable in Prometheus
- Both Grafana dashboards auto-provisioned at boot
- Drift alerts correctly pending for templated seed data (expected — KS flags narrow distributions against a normal-synthetic baseline)

Problems faced:
- KS test against a synthetic-normal reference built from baseline mean+std flags very narrow live distributions (like templated text) as drift. Acceptable for Phase 6; will settle once Phase 10 real data lands.
- mlflow models serve doesn't expose `/metrics` natively. Rather than add a sidecar exporter for the model server, deferred — API-side metrics plus the `up{job="api"}` signal cover serving availability for grading purposes.
## Phase 7 — Frontend + pipeline viz screens — ⏳ pending
## Phase 8 — CI/CD + rollback — ⏳ pending
## Phase 9 — Feedback loop + retraining — ⏳ pending
## Phase 10 — FinBERT + quantization — ⏳ pending
## Phase 11 — Tests + report — ⏳ pending
## Phase 12 — Security hardening — ⏳ pending
## Phase 13 — Demo polish + viva prep — ⏳ pending
