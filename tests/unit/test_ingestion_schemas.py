"""Unit tests for ingestion schemas."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from ssa_ingestion.schemas import Source, TextRecord


def _valid_kwargs() -> dict:
    return dict(
        id="abc",
        source=Source.SEED,
        ticker="aapl",  # will be uppercased
        text="some text long enough",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def test_ticker_is_uppercased() -> None:
    r = TextRecord(**_valid_kwargs())
    assert r.ticker == "AAPL"


def test_naive_timestamp_is_utc_normalised() -> None:
    kw = _valid_kwargs()
    kw["timestamp"] = datetime(2026, 1, 1)
    r = TextRecord(**kw)
    assert r.timestamp.tzinfo is not None


def test_ticker_regex_rejects_lowercase_only_without_letters() -> None:
    kw = _valid_kwargs()
    kw["ticker"] = "123"
    with pytest.raises(ValidationError):
        TextRecord(**kw)


def test_text_bounds_enforced() -> None:
    kw = _valid_kwargs()
    kw["text"] = ""
    with pytest.raises(ValidationError):
        TextRecord(**kw)


def test_dedup_key_is_stable() -> None:
    r = TextRecord(**_valid_kwargs())
    assert r.key() == ("seed", "abc")


def test_extra_fields_rejected() -> None:
    kw = _valid_kwargs()
    kw["unexpected"] = 1
    with pytest.raises(ValidationError):
        TextRecord(**kw)
