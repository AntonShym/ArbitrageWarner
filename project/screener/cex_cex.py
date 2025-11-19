"""CEX -> CEX arbitrage scanning logic."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from project.core.data_sources.hb_cex import HummingbotCexDataSource
from project.core.models.signal import ArbitrageSignal, SignalRow
from project.core.utils.math import calculate_dif, calculate_profit
from project.core.utils.time import utc_timestamp
from project.screener.classify import classify_signal


@dataclass
class CexMarketConfig:
    exchange: str
    trading_pair: str
    chain: Optional[str] = None


class CexCexScreener:
    """Finds profitable spreads between centralized exchanges."""

    def __init__(
        self,
        markets: Iterable[CexMarketConfig],
        min_difference: float,
        target_value: float,
        data_source: Optional[HummingbotCexDataSource] = None,
    ) -> None:
        self.markets = list(markets)
        self.min_difference = min_difference
        self.target_value = target_value
        self.data_source = data_source or HummingbotCexDataSource()

    async def _fetch_quotes(self, trading_pair: str) -> Dict[str, Tuple[float, float]]:
        exchanges = [market.exchange for market in self.markets if market.trading_pair == trading_pair]
        return await self.data_source.gather_best_prices(exchanges, trading_pair)

    def _build_signal(
        self,
        trading_pair: str,
        best_buy: Tuple[str, Tuple[float, float]],
        best_sell: Tuple[str, Tuple[float, float]],
    ) -> Optional[ArbitrageSignal]:
        buy_exchange, (_, best_ask) = best_buy
        sell_exchange, (best_bid, _) = best_sell
        if best_bid <= 0 or best_ask <= 0:
            return None
        dif = calculate_dif(best_ask, best_bid)
        if dif < self.min_difference:
            return None
        amount = self.target_value / best_ask
        profit = calculate_profit(best_ask, best_bid, amount)
        rows = [
            SignalRow(buy_exchange, -dif, -profit, self.target_value, best_ask, chain=None),
            SignalRow(sell_exchange, dif, profit, self.target_value, best_bid, chain=None),
        ]
        base, quote = trading_pair.split("-")
        return ArbitrageSignal(
            pair=trading_pair,
            base=base,
            quote=quote,
            signal_type="cex_cex",
            direction=f"{buy_exchange} -> {sell_exchange}",
            sell_price=best_bid,
            amount=amount,
            value=self.target_value,
            value_max=self.target_value,
            rows=rows,
            classification=classify_signal(dif),
            timestamp=utc_timestamp(),
        )

    async def scan_pair(self, trading_pair: str) -> Optional[ArbitrageSignal]:
        quotes = await self._fetch_quotes(trading_pair)
        if len(quotes) < 2:
            return None
        best_buy = min(quotes.items(), key=lambda item: item[1][1])
        best_sell = max(quotes.items(), key=lambda item: item[1][0])
        if best_buy[0] == best_sell[0]:
            return None
        return self._build_signal(trading_pair, best_buy, best_sell)

    async def scan(self, trading_pairs: Iterable[str]) -> List[ArbitrageSignal]:
        tasks = [self.scan_pair(pair) for pair in trading_pairs]
        results = await asyncio.gather(*tasks)
        return [signal for signal in results if signal]

