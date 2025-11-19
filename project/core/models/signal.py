"""Unified arbitrage signal model."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SignalRow:
    """Single row of opportunity metadata."""

    exc: str
    dif: float
    prof: float
    value: float
    price: float
    chain: Optional[str] = None
    extra: Dict[str, str] = field(default_factory=dict)


@dataclass
class ArbitrageSignal:
    """Canonical arbitrage signal structure."""

    pair: str
    base: str
    quote: str
    signal_type: str
    direction: str
    sell_price: float
    amount: float
    value: float
    value_max: float
    rows: List[SignalRow]
    classification: str
    timestamp: float
    lifetime_sec: float = 0.0
    timeout_sec: float = 0.0

    def identity(self) -> str:
        """Unique identifier used for deduplication."""
        if not self.rows:
            return f"{self.signal_type}:{self.pair}"
        first = self.rows[0]
        last = self.rows[-1]
        return f"{self.signal_type}:{self.pair}:{first.exc}:{last.exc}"

