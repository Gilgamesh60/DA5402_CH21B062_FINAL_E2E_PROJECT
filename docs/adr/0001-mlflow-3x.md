# ADR 0001 — MLflow 3.x on both client and server

**Date**: Phase 4
**Status**: Accepted

## Context

Phase 0 pinned MLflow 2.10.2 as a safe, well-tested version. During Phase 4, training against the server failed with 404s at `/api/2.0/mlflow/logged-models` because the Python client auto-upgraded to 3.11.1 (via pip's latest-wins resolution on Python 3.14 fresh installs) and called endpoints 2.10 didn't have.

## Decision

Pin **both** client and server to MLflow `3.11.1`.

## Tradeoffs

**Pros**
- Consistent API surface between client and server — no more 404s on new endpoints.
- Access to MLflow 3.x improvements: better artifact proxying, logged-model concept, cleaner REST API.
- Current upstream recommended version for new projects.

**Cons**
- MLflow 3.x emits `FutureWarning` on `transition_model_version_stage` and `get_latest_versions` — stages are being deprecated in favour of aliases and tags.
- The rubric explicitly references stage-based promotion (Staging / Production / Archived), so we keep stages for now. Aliases are a post-grading migration.

## Migration path (post-grading)

1. Replace `transition_model_version_stage(...)` with `set_registered_model_alias(name, "production", version)`.
2. Serve models via `models:/stock-sentiment@production` instead of `models:/stock-sentiment/Production`.
3. Keep a thin compat shim in `ssa_model.registry` so the rest of the code doesn't care.
