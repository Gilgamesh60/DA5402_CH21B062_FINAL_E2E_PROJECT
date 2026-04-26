"""Reddit adapter via PRAW. Disabled when credentials aren't set."""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from typing import Iterable

import structlog

from ssa_ingestion.schemas import Source, TextRecord

logger = structlog.get_logger()

# Matches standalone upper-case ticker-like tokens, e.g. AAPL, TSLA, BRK.A
TICKER_TOKEN_RE = re.compile(r"(?<![A-Za-z])\$?([A-Z]{1,5}(?:\.[A-Z])?)(?![A-Za-z])")


class RedditSource:
    name = Source.REDDIT.value

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        user_agent: str | None = None,
        subreddits: list[str] | None = None,
    ) -> None:
        self.client_id = client_id or os.getenv("REDDIT_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("REDDIT_CLIENT_SECRET")
        self.user_agent = user_agent or os.getenv(
            "REDDIT_USER_AGENT", "stock-sentiment-mlops/0.1"
        )
        self.subreddits = subreddits or ["wallstreetbets", "stocks", "investing"]
        self._client = None
        if not (self.client_id and self.client_secret):
            logger.info("reddit_disabled_no_credentials")

    def _client_or_none(self):
        if self._client is not None:
            return self._client
        if not (self.client_id and self.client_secret):
            return None
        try:
            import praw  # lazy import

            self._client = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent,
                check_for_async=False,
            )
            return self._client
        except Exception as e:
            logger.warning("reddit_client_init_failed", error=str(e))
            return None

    def fetch(
        self,
        tickers: list[str],
        lookback_hours: int,
        max_items: int,
    ) -> Iterable[TextRecord]:
        client = self._client_or_none()
        if client is None:
            return
        ticker_set = {t.upper() for t in tickers}
        since = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        emitted = 0
        for sub in self.subreddits:
            if emitted >= max_items:
                break
            try:
                for post in client.subreddit(sub).new(limit=max_items):
                    created = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
                    if created < since:
                        continue
                    body = " ".join(filter(None, [post.title, getattr(post, "selftext", "")]))
                    hits = set(TICKER_TOKEN_RE.findall(body)) & ticker_set
                    for ticker in hits:
                        try:
                            yield TextRecord(
                                id=f"reddit-{post.id}-{ticker}",
                                source=Source.REDDIT,
                                ticker=ticker,
                                text=body[:5000],
                                timestamp=created,
                                title=post.title,
                                url=f"https://reddit.com{post.permalink}",
                                author=str(post.author) if post.author else None,
                            )
                            emitted += 1
                        except Exception as e:
                            logger.warning("reddit_bad_post", error=str(e))
                        if emitted >= max_items:
                            return
            except Exception as e:
                logger.warning("reddit_subreddit_failed", subreddit=sub, error=str(e))
                continue
