"""Data models for market quotes and arbitrage signals."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class CexQuote:
    """Represents best bid/ask snapshot for a connector."""

    connector: str
    symbol: str
    bid: Optional[float]
    ask: Optional[float]
    timestamp: float

    def has_spread(self) -> bool:
        return self.bid is not None and self.ask is not None and self.ask > 0

    @property
    def mid_price(self) -> Optional[float]:
        if self.bid is None or self.ask is None:
            return None
        return (self.bid + self.ask) / 2


@dataclass
class CexCexSignal:
    """Structured CEX-CEX opportunity enriched with signal metrics."""

    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    dif: float
    prof: float
    value: float
    amount: float
    price: float
    chain: Optional[str]
    timestamp: float

    @property
    def spread_percent(self) -> float:
        return self.dif

    @property
    def profit_usd(self) -> float:
        return self.prof
