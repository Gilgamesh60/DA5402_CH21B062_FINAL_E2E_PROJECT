.PHONY: help install up down logs ps rebuild test lint format clean rollback dag test-report

help:
	@echo "Common targets:"
	@echo "  make install     Install Python deps (editable + dev extras)"
	@echo "  make up          Boot the full stack in the background"
	@echo "  make down        Stop and remove containers"
	@echo "  make logs        Tail logs from all services"
	@echo "  make ps          Show service status"
	@echo "  make rebuild     Rebuild custom images from scratch"
	@echo "  make test        Run unit tests"
	@echo "  make lint        Run ruff, black --check, isort --check, mypy"
	@echo "  make format      Auto-format with black + isort + ruff --fix"
	@echo "  make dag         Print + export the DVC DAG"
	@echo "  make rollback V=<version>  Roll the registered model to V"
	@echo "  make clean       Remove caches and build artifacts"

install:
	pip install -e ".[dev,ingestion,model]"
	pre-commit install

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

ps:
	docker compose ps

rebuild:
	docker compose build --no-cache

test:
	pytest tests/unit -v

lint:
	ruff check src tests
	black --check src tests
	isort --check-only src tests
	mypy src || true  # relaxed until Phase 5

format:
	black src tests
	isort src tests
	ruff check --fix src tests

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache build dist *.egg-info
	find . -name __pycache__ -type d -exec rm -rf {} +

dag:
	dvc dag
	mkdir -p docs/diagrams
	dvc dag --dot > docs/diagrams/dvc-dag.dot
	@echo "wrote docs/diagrams/dvc-dag.dot"

rollback:
	@if [ -z "$(V)" ]; then echo "Usage: make rollback V=<version> [RESTART=1]"; exit 1; fi
	@if [ "$(RESTART)" = "1" ]; then \
		python scripts/rollback.py $(V) --restart; \
	else \
		python scripts/rollback.py $(V); \
	fi

test-report:
	@mkdir -p artifacts docs
	pytest tests/unit tests/integration tests/contract tests/e2e \
		--junitxml=artifacts/junit.xml \
		--cov=src --cov-report=xml || true
	python scripts/verify_acceptance.py
	python scripts/generate_test_report.py
	@echo "wrote docs/test-report.md"
