"""Generate a labelled seed corpus for offline pipeline runs.

Deterministic — uses a fixed seed — so the output is reproducible.
Writes `data/seed/seed_corpus.jsonl` with ~300 labelled records
across a handful of tickers.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META"]

POSITIVE_TEMPLATES = [
    "{t} reports record quarterly earnings, beating analyst estimates by a wide margin.",
    "Analysts upgrade {t} to a Strong Buy on robust demand and expanding margins.",
    "{t} unveils breakthrough product that investors are calling a category winner.",
    "Bullish sentiment for {t} grows as the company raises full-year guidance.",
    "{t} stock surges after a landmark partnership announcement boosts growth prospects.",
    "Institutional inflows into {t} accelerate as the fundamentals continue to strengthen.",
    "Strong cash flow and a rising dividend make {t} a standout pick this quarter.",
    "{t} sees record user growth this quarter, beating its own ambitious targets.",
]

NEGATIVE_TEMPLATES = [
    "{t} misses revenue expectations, shares slide in after-hours trading.",
    "Regulatory scrutiny on {t} intensifies, raising concerns about future fines.",
    "Analysts downgrade {t} amid concerns about slowing demand and rising costs.",
    "{t} warns of a weaker outlook, citing macro headwinds and supply constraints.",
    "Shares of {t} tumble after a disappointing product launch and executive departure.",
    "Short interest in {t} climbs as bearish bets pile up on deteriorating metrics.",
    "Lawsuit against {t} expands, threatening a hit to profitability next year.",
    "{t} guidance comes in well below consensus, prompting a wave of sell ratings.",
]

NEUTRAL_TEMPLATES = [
    "{t} schedules its next earnings call for the end of the month.",
    "{t} files a routine 10-Q; contents largely in line with prior filings.",
    "{t} opens a new regional office; no immediate financial impact disclosed.",
    "CEO of {t} to speak at an industry conference next week on long-term strategy.",
    "{t} announces a minor leadership reshuffle in its operations division.",
    "Trading volume for {t} in line with its 30-day average.",
    "{t} updates its investor relations website; no new guidance issued.",
    "{t} confirms attendance at an upcoming technology trade show.",
]


def main() -> None:
    rng = random.Random(42)
    out = Path("data/seed/seed_corpus.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).replace(microsecond=0)

    records: list[dict] = []
    counter = 0
    # Slight class imbalance so baselines are realistic
    mix = [("positive", 110), ("negative", 95), ("neutral", 95)]
    for label, n in mix:
        templates = {
            "positive": POSITIVE_TEMPLATES,
            "negative": NEGATIVE_TEMPLATES,
            "neutral": NEUTRAL_TEMPLATES,
        }[label]
        for _ in range(n):
            t = rng.choice(TICKERS)
            text = rng.choice(templates).format(t=t)
            ts = now - timedelta(hours=rng.randint(0, 240), minutes=rng.randint(0, 59))
            counter += 1
            records.append(
                {
                    "id": f"seed-{counter:04d}",
                    "source": "seed",
                    "ticker": t,
                    "text": text,
                    "timestamp": ts.isoformat(),
                    "title": None,
                    "url": None,
                    "author": None,
                    "language": "en",
                    "label": label,
                }
            )

    rng.shuffle(records)
    with out.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    print(f"wrote {len(records)} records to {out}")


if __name__ == "__main__":
    main()
