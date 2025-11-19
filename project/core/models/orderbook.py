"""Order book data structures and helper functions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple


@dataclass
class OrderBookEntry:
    """Single price level entry."""

    price: float
    amount: float


@dataclass
class OrderBookSnapshot:
    """Aggregated order book snapshot with helper utilities."""

    trading_pair: str
    bids: Sequence[OrderBookEntry]
    asks: Sequence[OrderBookEntry]

    def best_bid(self) -> float:
        return self.bids[0].price if self.bids else 0.0

    def best_ask(self) -> float:
        return self.asks[0].price if self.asks else 0.0

    def vwap_price(self, side: str, quote_value: float) -> float:
        """Compute VWAP for the requested quote notional."""
        entries = self.asks if side == "buy" else self.bids
        remaining = quote_value
        total_quote_spent = 0.0
        total_base = 0.0

        for entry in entries:
            level_quote = entry.price * entry.amount
            if remaining <= 0:
                break
            if level_quote >= remaining:
                partial_base = remaining / entry.price
                total_quote_spent += remaining
                total_base += partial_base
                remaining = 0.0
            else:
                total_quote_spent += level_quote
                total_base += entry.amount
                remaining -= level_quote

        if remaining > 0 or total_base <= 0:
            raise RuntimeError(f"Not enough liquidity on {self.trading_pair} to fill {quote_value}$")
        return total_quote_spent / total_base


def build_entries(raw_entries: Iterable[Tuple[float, float]]) -> List[OrderBookEntry]:
    """Transform hummingbot tuples into OrderBookEntry objects."""
    return [OrderBookEntry(price=float(price), amount=float(amount)) for price, amount in raw_entries]

