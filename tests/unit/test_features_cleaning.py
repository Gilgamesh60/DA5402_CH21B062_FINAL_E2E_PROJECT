"""Unit tests for text cleaning."""

from __future__ import annotations

from ssa_features.cleaning import CleaningConfig, clean_text


def test_empty_text_returns_empty_string() -> None:
    assert clean_text("") == ""
    assert clean_text(None) == ""  # type: ignore[arg-type]


def test_url_is_removed() -> None:
    out = clean_text("check https://example.com/path?q=1 now")
    assert "http" not in out
    assert "example" not in out
    assert "check" in out and "now" in out


def test_mentions_are_removed() -> None:
    out = clean_text("@jim said $AAPL is great")
    assert "@jim" not in out
    assert "aapl" in out


def test_cashtag_preserved_as_ticker() -> None:
    # $AAPL -> AAPL (lowercased by default), then tokenised cleanly
    out = clean_text("$AAPL surged today")
    assert "aapl" in out.split()


def test_lowercase_on_by_default() -> None:
    assert clean_text("HELLO WORLD") == "hello world"


def test_whitespace_collapsed() -> None:
    assert clean_text("a    b\t\nc") == "a b c"


def test_unicode_normalised() -> None:
    # precomposed vs decomposed é should both produce the same output
    assert clean_text("café") == clean_text("cafe\u0301")


def test_edge_punctuation_stripped() -> None:
    assert clean_text("...hello!!!") == "hello"


def test_config_disables_lowercase() -> None:
    cfg = CleaningConfig(lowercase=False)
    assert clean_text("HELLO", cfg) == "HELLO"
