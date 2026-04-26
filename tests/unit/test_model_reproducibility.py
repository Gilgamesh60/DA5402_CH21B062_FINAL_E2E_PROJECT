"""Unit tests for reproducibility helpers."""

from __future__ import annotations

import json
from pathlib import Path

from ssa_model import reproducibility as r


def test_git_commit_sha_is_nonempty_in_this_repo() -> None:
    sha = r.git_commit_sha()
    assert sha != "unknown"
    assert len(sha) == 40


def test_hardware_fingerprint_has_expected_keys() -> None:
    hw = r.hardware_fingerprint()
    for key in ("python_version", "platform", "machine", "cpu_count"):
        assert key in hw


def test_full_context_serialises_cleanly(tmp_path: Path) -> None:
    ctx = r.full_context()
    # must be JSON-serialisable end-to-end
    s = json.dumps(ctx)
    loaded = json.loads(s)
    assert "git" in loaded
    assert "hardware" in loaded


def test_write_context_artifact_creates_file(tmp_path: Path) -> None:
    out = r.write_context_artifact(tmp_path / "ctx.json")
    assert out.exists()
    parsed = json.loads(out.read_text())
    assert "git" in parsed


def test_dvc_data_hash_graceful_when_missing(tmp_path: Path) -> None:
    assert r.dvc_data_hash(tmp_path / "missing.lock") == "unknown"
