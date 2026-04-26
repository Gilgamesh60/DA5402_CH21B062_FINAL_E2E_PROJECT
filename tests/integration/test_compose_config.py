"""Integration test: docker-compose config parses cleanly.

Doesn't require Docker to be running — just that the compose CLI is
installed. Catches regressions in the service definitions before they
hit CI.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skipif(shutil.which("docker") is None, reason="docker not installed")
def test_compose_config_is_valid() -> None:
    result = subprocess.run(
        ["docker", "compose", "config", "--quiet"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"compose config failed: {result.stderr}"


@pytest.mark.skipif(shutil.which("docker") is None, reason="docker not installed")
def test_compose_has_expected_services() -> None:
    result = subprocess.run(
        ["docker", "compose", "config", "--services"],
        capture_output=True,
        text=True,
        check=True,
    )
    services = set(result.stdout.strip().splitlines())
    expected = {
        "postgres",
        "mlflow",
        "model-server",
        "api",
        "airflow-init",
        "airflow-webserver",
        "airflow-scheduler",
        "prometheus",
        "grafana",
        "frontend",
        "drift-exporter",
    }
    missing = expected - services
    assert not missing, f"missing services: {missing}"
