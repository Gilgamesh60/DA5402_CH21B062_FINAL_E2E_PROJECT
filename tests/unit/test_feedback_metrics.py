"""Unit tests for the feedback metrics renderer (no DB required)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ssa_monitoring.feedback_metrics import render_prom


def _report(**kwargs) -> dict:
    base = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "feedback_total": 0,
        "agreement_rate": None,
        "per_model_version": [],
    }
    base.update(kwargs)
    return base


def test_renders_minimal_report(tmp_path: Path) -> None:
    out = render_prom(_report(), tmp_path / "f.prom")
    body = out.read_text()
    assert "feedback_total 0" in body
    assert "feedback_last_run_timestamp" in body
    # No agreement_rate or per_model_version when absent
    assert "feedback_agreement_rate" not in body
    assert "feedback_accuracy_by_model" not in body


def test_renders_full_report(tmp_path: Path) -> None:
    out = render_prom(
        _report(
            feedback_total=42,
            agreement_rate=0.78,
            per_model_version=[
                {"model_version": "1", "n": 10, "accuracy": 0.7},
                {"model_version": "2", "n": 32, "accuracy": 0.82},
            ],
        ),
        tmp_path / "f.prom",
    )
    body = out.read_text()
    assert "feedback_total 42" in body
    assert "feedback_agreement_rate 0.78" in body
    assert 'feedback_accuracy_by_model{version="1"} 0.7' in body
    assert 'feedback_accuracy_by_model{version="2"} 0.82' in body
    # Exposition format sanity
    assert body.count("# HELP") >= 4
    assert body.count("# TYPE") >= 4
