"""Load ingestion params from the shared `params.yaml`."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class IngestionConfig:
    news_sources: list[str] = field(default_factory=list)
    news_lookback_hours: int = 24
    news_max_items_per_source: int = 500
    news_languages: list[str] = field(default_factory=lambda: ["en"])
    social_sources: list[str] = field(default_factory=list)
    social_subreddits: list[str] = field(default_factory=list)
    social_lookback_hours: int = 24
    social_max_posts: int = 1000
    tickers: list[str] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: Path | str = "params.yaml") -> "IngestionConfig":
        with Path(path).open("r", encoding="utf-8") as fh:
            raw: dict[str, Any] = yaml.safe_load(fh)
        ing = raw.get("ingestion", {})
        news = ing.get("news", {})
        social = ing.get("social", {})
        return cls(
            news_sources=list(news.get("sources", [])),
            news_lookback_hours=int(news.get("lookback_hours", 24)),
            news_max_items_per_source=int(news.get("max_items_per_source", 500)),
            news_languages=list(news.get("languages", ["en"])),
            social_sources=list(social.get("sources", [])),
            social_subreddits=list(social.get("subreddits", [])),
            social_lookback_hours=int(social.get("lookback_hours", 24)),
            social_max_posts=int(social.get("max_posts", 1000)),
            tickers=list(ing.get("tickers", [])),
        )


@dataclass
class ValidationConfig:
    required_fields: list[str] = field(
        default_factory=lambda: ["id", "ticker", "text", "timestamp", "source"]
    )
    min_text_length: int = 10
    max_text_length: int = 5000
    dedupe_on: list[str] = field(default_factory=lambda: ["id", "source"])
    allowed_languages: list[str] = field(default_factory=lambda: ["en"])

    @classmethod
    def from_file(cls, path: Path | str = "params.yaml") -> "ValidationConfig":
        with Path(path).open("r", encoding="utf-8") as fh:
            raw: dict[str, Any] = yaml.safe_load(fh)
        v = raw.get("validation", {})
        return cls(
            required_fields=list(
                v.get("required_fields", ["id", "ticker", "text", "timestamp", "source"])
            ),
            min_text_length=int(v.get("min_text_length", 10)),
            max_text_length=int(v.get("max_text_length", 5000)),
            dedupe_on=list(v.get("dedupe_on", ["id", "source"])),
            allowed_languages=list(v.get("allowed_languages", ["en"])),
        )
