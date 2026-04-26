# Stock Sentiment Analysis System — MLOps

An end-to-end AI application that predicts sentiment (positive / negative / neutral) for stocks from financial news and social media, built with a full MLOps lifecycle.

## Status

Phase 0 — Scaffolding and contracts. Nothing runs yet.

## Problem

Given a stock ticker, return an aggregated sentiment score (positive / negative / neutral) with a confidence value, computed from recent financial news and social media posts.

## Success metrics

- **ML metric**: macro-F1 ≥ 0.75 on held-out labelled financial sentiment data
- **Business metric**: `/predict` p95 latency < 200 ms under light load
- **Operational metric**: API error rate < 5%, feature drift score below threshold

Full criteria in [`docs/acceptance-criteria.md`](docs/acceptance-criteria.md).

## Architecture at a glance

Loose-coupled services, each in its own container, wired by `docker compose`:

| Service        | Role                                                  |
|----------------|-------------------------------------------------------|
| `frontend`     | Web UI (React + Vite). Talks to `api` via REST only.  |
| `api`          | FastAPI gateway. Validates requests, forwards to model server, emits Prometheus metrics. |
| `model-server` | `mlflow models serve` loading the registered model.   |
| `mlflow`       | Tracking server + Model Registry (Postgres-backed).   |
| `airflow`      | Ingestion, feature engineering, retraining DAGs.      |
| `postgres`     | Backend store for MLflow, Airflow, and feedback.      |
| `prometheus`   | Scrapes metrics from every service.                   |
| `grafana`      | Near-real-time dashboards and alerts.                 |

See [`docs/architecture.md`](docs/architecture.md) for the full diagram.

## Documentation

- [Architecture](docs/architecture.md)
- [High-Level Design](docs/HLD.md)
- [Low-Level Design](docs/LLD.md)
- [Acceptance Criteria](docs/acceptance-criteria.md)
- [Test Plan](docs/test-plan.md)
- [User Manual](docs/user-manual.md) — written in Phase 13
- [References](docs/references/) — original course guideline PDFs

## Repository layout

```
.
├── docs/                # All design docs, diagrams, references
├── src/
│   ├── ssa_ingestion/   # News + social data ingestion
│   ├── ssa_features/    # Feature engineering (versioned separately)
│   ├── ssa_model/       # Training, evaluation, registry interaction
│   ├── ssa_api/         # FastAPI gateway
│   └── ssa_monitoring/  # Drift detection, exporters
├── frontend/            # React + Vite UI
├── airflow/dags/        # Ingestion + retraining DAGs
├── docker/              # Dockerfiles per service
├── prometheus/          # Scrape config + alert rules
├── grafana/             # Dashboards + datasources
├── tests/               # Unit, integration, contract tests
├── notebooks/           # EDA
├── artifacts/           # Baselines, reports (DVC-tracked)
├── dvc.yaml             # Pipeline DAG (data → features → train → evaluate)
├── params.yaml          # Hyperparameters and pipeline config
├── MLproject            # Identical dev/test environments
├── docker-compose.yml   # Multi-service orchestration
└── pyproject.toml       # Python packaging
```

## Quick start

```bash
# Install Python deps (editable install of all packages)
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Boot the full stack (Phase 1+ only)
docker compose up -d
```

## License

Course project — not for redistribution.
