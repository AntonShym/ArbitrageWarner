"""Legacy quote models used by quants-lab adapters."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class CexQuote:
    connector: str
    symbol: str
    bid: Optional[float]
    ask: Optional[float]
    timestamp: float

    def has_spread(self) -> bool:
        return self.bid is not None and self.ask is not None and self.ask > 0

