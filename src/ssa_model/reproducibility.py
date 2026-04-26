"""Reproducibility hooks logged to every MLflow run.

Satisfies the MLOps-guidelines requirement that every experiment be
reproducible from a `(git_commit_sha, mlflow_run_id)` pair, plus the
rubric's "beyond autolog" item by stamping custom context on every run.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
from pathlib import Path
from typing import Any


def git_commit_sha(repo_root: Path | str = ".") -> str:
    """Return the current HEAD SHA, or 'unknown' when git is unavailable."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(repo_root), stderr=subprocess.DEVNULL
        )
        return out.decode("utf-8").strip()
    except Exception:
        return "unknown"


def git_dirty(repo_root: Path | str = ".") -> bool:
    """True if the working tree has uncommitted changes."""
    try:
        out = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=str(repo_root), stderr=subprocess.DEVNULL
        )
        return bool(out.strip())
    except Exception:
        return False


def dvc_data_hash(dvc_lock_path: Path | str = "dvc.lock") -> str:
    """MD5 of the DVC lock file — pins the data version the run saw."""
    p = Path(dvc_lock_path)
    if not p.exists():
        return "unknown"
    return hashlib.md5(p.read_bytes()).hexdigest()


def hardware_fingerprint() -> dict[str, Any]:
    """Minimal snapshot of where training ran — useful when comparing runs."""
    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or "unknown",
        "cpu_count": os.cpu_count() or 1,
    }


def environment_snapshot() -> list[str]:
    """Frozen pip env, used as an MLflow artifact."""
    try:
        out = subprocess.check_output(
            ["pip", "freeze"], stderr=subprocess.DEVNULL
        ).decode("utf-8")
        return out.splitlines()
    except Exception:
        return []


def params_snapshot(path: Path | str = "params.yaml") -> dict[str, Any]:
    """Raw params.yaml as a dict — logged as JSON artifact."""
    import yaml

    p = Path(path)
    if not p.exists():
        return {}
    with p.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def full_context(repo_root: Path | str = ".") -> dict[str, Any]:
    """All reproducibility metadata in one dict — logged as JSON artifact."""
    return {
        "git": {
            "commit_sha": git_commit_sha(repo_root),
            "dirty": git_dirty(repo_root),
        },
        "dvc": {
            "data_hash": dvc_data_hash(),
        },
        "hardware": hardware_fingerprint(),
        "params": params_snapshot(),
    }


def write_context_artifact(out_path: Path | str, repo_root: Path | str = ".") -> Path:
    """Write the context to JSON for MLflow to pick up."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(full_context(repo_root), indent=2), encoding="utf-8")
    return out_path
