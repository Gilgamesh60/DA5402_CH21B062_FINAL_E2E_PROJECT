"""Deterministic text cleaning.

Stateless transformations — same input always gives the same output.
That makes this module trivial to unit-test and to reason about under
drift conditions.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

URL_RE = re.compile(r"https?://\S+|www\.\S+")
MENTION_RE = re.compile(r"@[A-Za-z0-9_]+")
CASHTAG_RE = re.compile(r"\$([A-Za-z]{1,5})\b")
MULTI_WS_RE = re.compile(r"\s+")
PUNCT_EDGE_RE = re.compile(r"^[^\w$]+|[^\w$]+$")


@dataclass(frozen=True)
class CleaningConfig:
    """Switches for the cleaning pipeline — mirrors `params.yaml`."""

    lowercase: bool = True
    remove_urls: bool = True
    # When True, strip $TICKER markers (e.g. '$AAPL' -> 'AAPL'); when False,
    # drop them entirely. Financial text benefits from preserving the symbol.
    preserve_cashtags: bool = True
    remove_mentions: bool = True
    normalize_unicode: bool = True
    collapse_whitespace: bool = True


def clean_text(text: str, config: CleaningConfig | None = None) -> str:
    """Apply the configured cleaning steps.

    Returns an empty string when the input is falsy so downstream code
    can filter on length without NullPointer-style branching.
    """
    if not text:
        return ""
    cfg = config or CleaningConfig()
    out = text

    if cfg.normalize_unicode:
        out = unicodedata.normalize("NFKC", out)
    if cfg.remove_urls:
        out = URL_RE.sub(" ", out)
    if cfg.remove_mentions:
        out = MENTION_RE.sub(" ", out)
    if cfg.preserve_cashtags:
        out = CASHTAG_RE.sub(r"\1", out)
    if cfg.lowercase:
        out = out.lower()
    if cfg.collapse_whitespace:
        out = MULTI_WS_RE.sub(" ", out).strip()
    out = PUNCT_EDGE_RE.sub("", out)
    return out
