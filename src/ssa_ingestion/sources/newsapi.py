"""NewsAPI adapter. Disabled when NEWSAPI_KEY is unset."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Iterable

import structlog

from ssa_ingestion.schemas import Source, TextRecord

logger = structlog.get_logger()

BASE_URL = "https://newsapi.org/v2/everything"


class NewsApiSource:
    name = Source.NEWSAPI.value

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("NEWSAPI_KEY")
        if not self.api_key:
            logger.info("newsapi_disabled_no_key")

    def fetch(
        self,
        tickers: list[str],
        lookback_hours: int,
        max_items: int,
    ) -> Iterable[TextRecord]:
        if not self.api_key:
            return
        import requests  # lazy import; only needed when enabled

        since = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        emitted = 0
        for ticker in tickers:
            if emitted >= max_items:
                break
            try:
                r = requests.get(
                    BASE_URL,
                    params={
                        "q": ticker,
                        "from": since.isoformat(timespec="seconds"),
                        "language": "en",
                        "sortBy": "publishedAt",
                        "pageSize": min(100, max_items - emitted),
                    },
                    headers={"X-Api-Key": self.api_key},
                    timeout=15,
                )
                r.raise_for_status()
                articles = r.json().get("articles", [])
            except Exception as e:
                logger.warning("newsapi_fetch_failed", ticker=ticker, error=str(e))
                continue

            for a in articles:
                try:
                    text = " ".join(filter(None, [a.get("title"), a.get("description")]))
                    if not text:
                        continue
                    record = TextRecord(
                        id=a.get("url") or f"{ticker}-{a.get('publishedAt')}",
                        source=Source.NEWSAPI,
                        ticker=ticker,
                        text=text[:5000],
                        timestamp=datetime.fromisoformat(
                            a["publishedAt"].replace("Z", "+00:00")
                        ),
                        title=a.get("title"),
                        url=a.get("url"),
                        author=a.get("author"),
                    )
                except Exception as e:
                    logger.warning("newsapi_bad_article", error=str(e))
                    continue
                yield record
                emitted += 1
                if emitted >= max_items:
                    break
