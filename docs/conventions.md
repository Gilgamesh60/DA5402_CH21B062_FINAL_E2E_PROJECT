# Project conventions

## Python

- Python 3.10+
- `black` for formatting (line length 100)
- `ruff` for linting
- `isort` (black profile) for imports
- `mypy --strict` for type checks
- Pre-commit runs all of the above on every commit

## Logging

- Structured JSON logs via `structlog`
- Every log line includes: `timestamp`, `level`, `service`, `request_id` (when applicable), `event`
- Log levels: DEBUG for dev only, INFO for normal flow, WARNING for retryable, ERROR for handled failures, CRITICAL for process-ending

## Exceptions

- Catch narrow, re-raise wide at service boundaries
- Every service boundary (HTTP handler, Airflow task, DVC stage) has a top-level try/except that logs with context and surfaces a stable error code
- Never silently swallow — log and re-raise if you must

## Docstrings

- Google-style for every public function and class
- Module-level docstring for every file

## Commit messages

- Conventional Commits (`feat:`, `fix:`, `docs:`, etc.)
- Subject line ≤ 50 chars, imperative mood
- Body explains _why_, not _how_
- Include SIM / task link when relevant

## Branching

- Single-developer project → trunk-based on `main` with short-lived feature branches
- Every merge to `main` must pass CI

## File layout

- Source under `src/<package_name>/`
- Tests mirror source under `tests/unit/<package_name>/`
- Notebooks in `notebooks/` — never imported by source code
- Generated artifacts in `artifacts/` (DVC-tracked)
- Raw data in `data/raw/` (DVC-tracked, never committed to git)
