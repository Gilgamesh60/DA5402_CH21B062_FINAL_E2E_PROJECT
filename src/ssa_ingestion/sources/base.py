"""Protocol defining the contract every source must honor."""

from __future__ import annotations

from typing import Iterable, Protocol

from ssa_ingestion.schemas import TextRecord


class DataSource(Protocol):
    """Pull text records for a set of tickers over a time window.

    Implementations must be side-effect-free apart from outbound HTTP
    and must never raise on empty results — return an empty iterable.
    """

    name: str

    def fetch(
        self,
        tickers: list[str],
        lookback_hours: int,
        max_items: int,
    ) -> Iterable[TextRecord]:
        """Yield records. Implementations should log and skip bad items."""
        ...
