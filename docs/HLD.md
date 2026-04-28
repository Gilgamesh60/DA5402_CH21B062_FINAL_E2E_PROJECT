# High-Level Design

## 1. Problem statement

Given a stock ticker symbol, produce an aggregated sentiment classification (positive / negative / neutral) with a calibrated confidence score, derived from recent financial news articles and social media posts referencing the ticker.

## 2. Goals and non-goals

### Goals
- Accurate sentiment classification on financial text (macro-F1 ≥ 0.75)
- Low-latency inference (< 200 ms p95 under light load)
- Fully reproducible experiments (git SHA + MLflow run ID + DVC data hash)
- Automated data pipeline, CI, monitoring, and retraining
- Local-only deployment (no cloud)

### Non-goals
- Real-time trading signals or portfolio advice
- Multi-language support beyond English
- User authentication (this is a single-tenant demo)
- Horizontal scaling beyond a single Docker host

## 3. Design paradigm

**Modular, primarily functional with OO boundaries at service edges.**

- Pure functions for data transformations (easy to unit test, DVC-friendly)
- Classes for things with lifecycle and state: MLflow clients, model wrappers, feature pipelines, HTTP app
- Clear package boundaries: ingestion → features → model → api → monitoring, each independently versioned

## 4. Core design decisions

### 4.1 Loose coupling between frontend and backend
The frontend is a static React bundle that only knows the backend through a runtime-configurable `VITE_API_BASE_URL`. No shared code, no shared build step. The frontend can be swapped for a CLI or a different UI framework without backend changes.

### 4.2 Model server separate from API gateway
The API gateway (`ssa_api`) does **not** load the model. It forwards inference requests to a dedicated `model-server` container running `mlflow models serve`. Benefits:

- Satisfies "MLflow API-ification" rubric item
- Rollback is a registry stage transition, not a redeploy
- API can stay up across model reloads
- Matches the 3-container topology from the MLOps guidelines

### 4.3 Feature engineering as an independent Python package
`ssa_features` is installable and versioned on its own. Rationale:

- MLOps guidelines: "version their feature engineering logic separately from model logic"
- Lets us ship a feature-only change (e.g., new tokenizer) without touching model code
- Encourages thinking about features as data products

### 4.4 DVC DAG as the CI pipeline
The DVC DAG (`dvc.yaml`) describes the full lineage: ingest → validate → eda → features → train → evaluate. CI runs `dvc repro` in dry-run mode to validate the DAG and `pytest` for code. A rendered image of `dvc dag` lives in `docs/` and is displayed in the frontend pipeline viz screen.

### 4.5 Reproducibility contract
Every MLflow run records:
- `git.commit_sha` (via `git rev-parse HEAD` inside the training entry point)
- `dvc.data_hash` (MD5 of the `.dvc` pointer for the training data)
- Full `params.yaml` snapshot
- `environment.yaml` snapshot
- Hardware fingerprint (CPU / RAM / quantization flags)

Any run can be reproduced from `(git_commit_sha, mlflow_run_id)` alone.

### 4.6 Model choice
- **Baseline**: TF-IDF + Logistic Regression. Proves the pipeline, fast to train, easy to explain.
- **Upgrade path**: FinBERT or DistilBERT fine-tuned on financial sentiment data. Dynamically quantized via `torch.quantization.quantize_dynamic` to meet the 200 ms latency budget on CPU-only local hardware.
- Baseline retained as a fallback model in the registry for rollback demos.

### 4.7 Data sources
- **News**: NewsAPI + Finnhub (both have free tiers, keys held in `.env`)
- **Social**: Reddit via PRAW (subreddits: `wallstreetbets`, `stocks`, `investing`)
- **Labelled training data**: Financial PhraseBank + FiQA sentiment dataset (public, for initial training)

### 4.8 Monitoring and alerting
Prometheus scrapes every service at 5-second intervals. Grafana dashboards cover: API SLOs, pipeline run status, drift heatmap, prediction distribution, feedback-derived F1 decay, throughput. Alert rules fire when:
- API error rate > 5% over 5-minute window
- p95 latency > 200 ms
- Any feature drift p-value < 0.05
- Prediction class ratio deviates > 2σ from baseline

Alerts webhook into the Airflow retraining DAG.

### 4.9 Rollback mechanism
Triggered manually via the frontend "Models" screen or the GitHub Actions `rollback` workflow:
1. Identify previous Production-stage version in registry
2. Transition current Production → Archived
3. Transition previous version → Production
4. `docker compose restart model-server`
5. Post-rollback health check

### 4.10 Security posture
- All secrets in `.env` (gitignored); `.env.example` committed
- Postgres not exposed outside the docker network
- Services communicate on an internal docker network only; only frontend and api ports are exposed to the host
- Document local-dev TLS exception in `docs/security.md` (future)

## 5. Scalability

Single-host scope. Scale-out options documented but not implemented:
- Gunicorn with multiple Uvicorn workers behind the FastAPI container
- `docker compose up --scale model-server=N` + HAProxy
- Partition Airflow DAGs by ticker cohort

## 6. Explainability

- Baseline model: feature importance via logistic regression coefficients, logged as MLflow artifact per run
- Transformer model: attention-weight heatmaps for top contributing tokens, rendered in the frontend result view

## 7. Risks and mitigations

| Risk | Mitigation |
|---|---|
| FinBERT OOM on local laptop | Dynamic quantization, batch size 1, fallback to DistilBERT |
| NewsAPI rate limits | Local caching, exponential backoff, Finnhub as secondary |
| Airflow DAG UID issues in Docker | Pin `AIRFLOW_UID=50000` in `.env` |
| MLflow registry race conditions | Postgres-backed store, not file-based |
| Drift false positives on small traffic | Minimum sample size gate before emitting drift metric |
| Reddit API changes | Abstraction layer; ingestion source is a plugin |

## 8. Open questions

- Do we label unlabeled live data via weak supervision for continuous learning, or only retrain on new public datasets?
- How do we handle ticker symbols that collide with English words (e.g., `IT`, `ON`)?
- Fast forwarding vs. sliding window for sentiment aggregation?


