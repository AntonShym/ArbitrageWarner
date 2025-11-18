"""Data models for market quotes and arbitrage opportunities."""
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


@dataclass
class CexArbitrageOpportunity:
    """Represents a profitable CEX-CEX spread."""

    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    spread_percent: float

    @property
    def spread_ratio(self) -> float:
        return (self.sell_price / self.buy_price) - 1 if self.buy_price else 0.0
