"""Seed data source — reads the committed fixture JSONL.

Lets the whole pipeline run offline and deterministically. The fixture
lives at `data/seed/seed_corpus.jsonl` and is loaded row-by-row into
`TextRecord` instances.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

import structlog

from ssa_ingestion.schemas import Source, TextRecord

logger = structlog.get_logger()

DEFAULT_SEED_PATH = Path("data/seed/seed_corpus.jsonl")


class SeedSource:
    """Yield records from a local JSONL fixture."""

    name = Source.SEED.value

    def __init__(self, path: Path = DEFAULT_SEED_PATH) -> None:
        self.path = path

    def fetch(
        self,
        tickers: list[str],
        lookback_hours: int,  # noqa: ARG002 — seed ignores time window
        max_items: int,
    ) -> Iterator[TextRecord]:
        if not self.path.exists():
            logger.warning("seed_not_found", path=str(self.path))
            return
        wanted = {t.upper() for t in tickers}
        emitted = 0
        with self.path.open("r", encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, start=1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    row = json.loads(line)
                    record = TextRecord(**row)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning("seed_bad_row", line=line_no, error=str(e))
                    continue
                if wanted and record.ticker not in wanted:
                    continue
                yield record
                emitted += 1
                if emitted >= max_items:
                    break
