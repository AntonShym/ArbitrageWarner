from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class SpreadSnapshot:
    """Represents bid/ask information for a specific exchange and symbol."""

    symbol: str
    exchange: str
    bid: float
    ask: float
    timestamp: datetime


@dataclass
class CexCexSignal:
    """Structured payload describing a CEX → CEX arbitrage opportunity."""

    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    dif: float
    profit: float
    value: float
    amount: float
    price: float
    classification: str
    chain: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def identity_key(self) -> tuple[str, str, str]:
        """Returns a tuple that uniquely identifies the current trade direction."""

        return (self.symbol, self.buy_exchange, self.sell_exchange)
