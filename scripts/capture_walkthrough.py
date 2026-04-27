"""Capture all walkthrough screenshots from the live stack.

Runs headless Chromium against each UI, writes PNGs to docs/screenshots/.
Also exercises the API first so the Analyze screen has a real result and
the Grafana dashboards show non-empty data.

Usage:  .venv/bin/python scripts/capture_walkthrough.py
"""

from __future__ import annotations

import time
from pathlib import Path

import httpx
from playwright.sync_api import Page, sync_playwright

OUT = Path("docs/screenshots")
OUT.mkdir(parents=True, exist_ok=True)

# Services (host-exposed ports from docker-compose)
FRONTEND = "http://localhost:3000"
API = "http://localhost:8000"
MLFLOW = "http://localhost:5000"
AIRFLOW = "http://localhost:8080"
PROMETHEUS = "http://localhost:9090"
GRAFANA = "http://localhost:3001"
ALERTMANAGER = "http://localhost:9093"
DRIFT_EXPORTER = "http://localhost:9101"


# -------------------------------------------------------------------------
# Seed some traffic so dashboards and the Analyze screen render non-empty
# -------------------------------------------------------------------------
def prime_api() -> None:
    print("  priming API with a few predictions + feedback…")
    client = httpx.Client(base_url=API, timeout=10.0)
    for ticker in ["AAPL", "MSFT", "NVDA", "TSLA", "GOOGL"]:
        for _ in range(2):
            try:
                client.post("/predict", json={"ticker": ticker, "lookback_hours": 48})
            except httpx.HTTPError:
                pass
    # One with explanations
    try:
        r = client.post(
            "/predict",
            json={"ticker": "AAPL", "lookback_hours": 72, "include_explanations": True},
        )
        if r.status_code == 200:
            client.post(
                "/feedback",
                json={
                    "ticker": "AAPL",
                    "prediction_request_id": r.json()["request_id"],
                    "true_label": "positive",
                },
            )
    except httpx.HTTPError:
        pass
    client.close()


# -------------------------------------------------------------------------
# Screenshot helpers
# -------------------------------------------------------------------------
def shot(page: Page, name: str, full_page: bool = True) -> None:
    path = OUT / f"{name}.png"
    page.screenshot(path=str(path), full_page=full_page)
    print(f"  ✓ {name}.png")


def goto(page: Page, url: str, wait_for: str | None = None) -> None:
    # Many SPAs (MLflow, Grafana) never reach `networkidle` because they poll.
    # `domcontentloaded` + an explicit selector wait + settle is more reliable.
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    if wait_for:
        try:
            page.wait_for_selector(wait_for, timeout=10000)
        except Exception:
            pass
    time.sleep(2.0)  # settle animations + async renders


# -------------------------------------------------------------------------
# Frontend screens
# -------------------------------------------------------------------------
def capture_frontend(page: Page) -> None:
    print("frontend:")

    # Analyze (default) — empty state
    goto(page, FRONTEND)
    shot(page, "01_frontend_analyze_empty")

    # Fill in and submit
    page.fill("input#ticker", "AAPL")
    page.check("input#explain")
    page.click("button[type=submit]")
    page.wait_for_selector("text=Probability breakdown", timeout=15000)
    time.sleep(1.5)
    shot(page, "02_frontend_analyze_result")

    # Pipelines
    goto(page, f"{FRONTEND}/pipelines", wait_for="text=ML pipeline")
    shot(page, "03_frontend_pipelines")

    # Models
    goto(page, f"{FRONTEND}/models", wait_for="text=Registry versions")
    shot(page, "04_frontend_models")

    # Health
    goto(page, f"{FRONTEND}/health", wait_for="text=Service status")
    time.sleep(3)  # let the 15s refresh cycle paint
    shot(page, "05_frontend_health")

    # User manual
    goto(page, f"{FRONTEND}/manual", wait_for="text=User manual")
    shot(page, "06_frontend_manual")


# -------------------------------------------------------------------------
# MLOps tool UIs
# -------------------------------------------------------------------------
def capture_api_docs(page: Page) -> None:
    print("api:")
    goto(page, f"{API}/docs", wait_for="text=Stock Sentiment API")
    time.sleep(1)
    shot(page, "07_api_swagger")


def capture_mlflow(page: Page) -> None:
    print("mlflow:")
    goto(page, f"{MLFLOW}/#/experiments", wait_for="text=Experiments")
    time.sleep(2)
    shot(page, "08_mlflow_experiments")
    goto(page, f"{MLFLOW}/#/models", wait_for="text=Models")
    time.sleep(2)
    shot(page, "09_mlflow_models")


def capture_airflow(page: Page) -> None:
    print("airflow:")
    goto(page, f"{AIRFLOW}/login/")
    try:
        page.fill("#username", "admin")
        page.fill("#password", "admin")
        page.press("#password", "Enter")
        page.wait_for_url(f"{AIRFLOW}/home", timeout=15000)
    except Exception as e:
        print(f"    airflow login fell back: {e}")
        goto(page, f"{AIRFLOW}/home")
    time.sleep(3)
    shot(page, "10_airflow_dags")

    # Capture the ssa_ingestion DAG grid view — shows actual task runs
    # with green/red squares per run, which is the "console to track
    # errors, failures, and successful runs" the rubric asks for.
    try:
        goto(page, f"{AIRFLOW}/dags/ssa_ingestion/grid")
        time.sleep(5)
        shot(page, "10b_airflow_dag_grid")
    except Exception as e:
        print(f"    airflow grid capture failed: {e}")


def capture_prometheus(page: Page) -> None:
    print("prometheus:")
    goto(page, f"{PROMETHEUS}/targets")
    time.sleep(2)
    shot(page, "11_prometheus_targets")

    goto(page, f"{PROMETHEUS}/alerts")
    time.sleep(2)
    shot(page, "12_prometheus_alerts")


def capture_grafana(page: Page) -> None:
    print("grafana:")
    # Anonymous viewer is enabled in our compose config, so no login.
    goto(page, f"{GRAFANA}/d/ssa-api-overview/stock-sentiment-api-overview?refresh=5s")
    time.sleep(4)
    shot(page, "13_grafana_api_overview")

    goto(page, f"{GRAFANA}/d/ssa-ml-monitoring/stock-sentiment-ml-monitoring?refresh=5s")
    time.sleep(4)
    shot(page, "14_grafana_ml_monitoring")


def capture_alertmanager(page: Page) -> None:
    print("alertmanager:")
    goto(page, f"{ALERTMANAGER}/#/alerts")
    time.sleep(2)
    shot(page, "15_alertmanager_alerts")


def capture_drift_exporter(page: Page) -> None:
    print("drift-exporter:")
    goto(page, f"{DRIFT_EXPORTER}/metrics")
    time.sleep(1)
    shot(page, "16_drift_exporter_metrics")


# -------------------------------------------------------------------------
# Main
# -------------------------------------------------------------------------
def main() -> None:
    prime_api()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,  # crisper screenshots
        )
        page = context.new_page()

        try:
            capture_frontend(page)
            capture_api_docs(page)
            capture_mlflow(page)
            capture_airflow(page)
            capture_prometheus(page)
            capture_grafana(page)
            capture_alertmanager(page)
            capture_drift_exporter(page)
        finally:
            context.close()
            browser.close()

    print(f"\ndone — screenshots in {OUT}/")


if __name__ == "__main__":
    main()
