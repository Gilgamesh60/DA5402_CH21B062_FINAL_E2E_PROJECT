.PHONY: help install up down logs ps rebuild test lint format clean

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
