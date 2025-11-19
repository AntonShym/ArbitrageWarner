"""DEX -> DEX arbitrage module (optional)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from project.core.data_sources.hb_dex import DexQuoteProvider
from project.core.models.signal import ArbitrageSignal, SignalRow
from project.core.utils.math import calculate_dif, calculate_profit
from project.core.utils.time import utc_timestamp
from project.screener.classify import classify_signal


@dataclass
class DexDexLeg:
    api: str
    buy_token: str
    sell_token: str
    target_value: float


class DexDexScreener:
    """Checks spreads between two DEX routers."""

    def __init__(self, leg_a: DexDexLeg, leg_b: DexDexLeg, min_difference: float) -> None:
        self.leg_a = leg_a
        self.leg_b = leg_b
        self.min_difference = min_difference
        self.provider_a = DexQuoteProvider(leg_a.api)
        self.provider_b = DexQuoteProvider(leg_b.api)

    async def scan(self) -> Optional[ArbitrageSignal]:
        quote_a = await self.provider_a.fetch_quote(self.leg_a.buy_token, self.leg_a.sell_token, self.leg_a.target_value)
        quote_b = await self.provider_b.fetch_quote(self.leg_b.buy_token, self.leg_b.sell_token, self.leg_b.target_value)
        dif = calculate_dif(quote_a.price, quote_b.price)
        if dif < self.min_difference:
            return None
        amount = self.leg_a.target_value / quote_a.price
        profit = calculate_profit(quote_a.price, quote_b.price, amount)
        rows = [
            SignalRow("DEX A", -dif, -profit, self.leg_a.target_value, quote_a.price, chain=None),
            SignalRow("DEX B", dif, profit, self.leg_b.target_value, quote_b.price, chain=None),
        ]
        return ArbitrageSignal(
            pair=f"{self.leg_a.sell_token}-{self.leg_a.buy_token}",
            base=self.leg_a.sell_token,
            quote=self.leg_a.buy_token,
            signal_type="dex_dex",
            direction="DEX A -> DEX B",
            sell_price=quote_b.price,
            amount=amount,
            value=self.leg_a.target_value,
            value_max=self.leg_a.target_value,
            rows=rows,
            classification=classify_signal(dif),
            timestamp=utc_timestamp(),
        )

