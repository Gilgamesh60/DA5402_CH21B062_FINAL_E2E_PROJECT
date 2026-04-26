# ADR 0002 — MLflow artifact proxying via the tracking server

**Date**: Phase 4
**Status**: Accepted

## Context

Default `mlflow server` configuration sets each new experiment's `artifact_location` to a local filesystem path (e.g. `/mlflow/artifacts/<id>`). Clients receiving that path then try to write artifacts directly to the server's filesystem, which fails with `OSError: Read-only file system: '/mlflow'` when the client is on the host machine and the server is a container — the path isn't a shared mount.

## Decision

Run the MLflow server with **proxied artifact mode**:
```
mlflow server \
    --backend-store-uri postgresql://... \
    --artifacts-destination /mlflow/artifacts \
    --default-artifact-root mlflow-artifacts:/ \
    --serve-artifacts
```

Clients then receive artifact URIs of the form `mlflow-artifacts:/...` and upload them over HTTP, letting the server write to its own local volume.

## Tradeoffs

**Pros**
- Works regardless of where the client runs (host, container, CI) — no shared filesystem required.
- Centralised write path through the tracking server makes artifact auth and auditing easier later.
- Matches the recommended MLflow production deployment pattern.

**Cons**
- One extra hop per artifact upload; throughput is bounded by the tracking server's HTTP layer, not raw disk. Irrelevant at project scale.
- Existing experiments created before this change have bad `artifact_location` values baked in. We wiped the Postgres `mlflow` database once to start clean.

## Related
- This is also why the `sentiment-classifier` experiment name exists — the original `stock-sentiment` and `ssa-sentiment` names had bad baked-in paths from earlier attempts.
