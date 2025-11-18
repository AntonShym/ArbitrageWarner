"""CEX-CEX arbitrage logic built on top of quants-lab data."""
from __future__ import annotations

import asyncio
import logging
from typing import Iterable, List, Optional, Tuple

from project.core.data_sources.quants_cex import QuantsLabCexDataSource
from project.core.models.quotes import CexCexSignal, CexQuote

logger = logging.getLogger(__name__)


class CexCexArbitrageScreener:
    """Scans multiple connectors for profitable spreads."""

    def __init__(
        self,
        connectors: Iterable[str],
        min_profit_percent: float,
        data_source: Optional[QuantsLabCexDataSource] = None,
        target_value: float = 1000.0,
        default_chain: Optional[str] = None,
    ):
        self.connectors = list(connectors)
        self.min_profit_percent = min_profit_percent
        self.target_value = max(0.0, float(target_value))
        self.default_chain = default_chain
        self.data_source = data_source or QuantsLabCexDataSource()

    @staticmethod
    def _select_best_quotes(quotes: List[CexQuote]) -> Optional[Tuple[CexQuote, CexQuote]]:
        best_buy = None
        best_sell = None

        for quote in quotes:
            if not quote.has_spread():
                continue
            if best_buy is None or (quote.ask or float("inf")) < (best_buy.ask or float("inf")):
                best_buy = quote
            if best_sell is None or (quote.bid or 0.0) > (best_sell.bid or 0.0):
                best_sell = quote

        if not best_buy or not best_sell or best_buy.connector == best_sell.connector:
            return None
        return best_buy, best_sell

    def _build_signal(self, buy: CexQuote, sell: CexQuote) -> Optional[CexCexSignal]:
        if buy.ask is None or sell.bid is None or buy.ask <= 0:
            return None
        spread_percent = ((sell.bid - buy.ask) / buy.ask) * 100
        if spread_percent <= 0:
            return None
        amount = (self.target_value / buy.ask) if self.target_value > 0 else 0.0
        if amount <= 0:
            return None
        value = amount * buy.ask
        profit = (sell.bid - buy.ask) * amount
        timestamp = max(buy.timestamp, sell.timestamp)
        return CexCexSignal(
            symbol=buy.symbol,
            buy_exchange=buy.connector,
            sell_exchange=sell.connector,
            buy_price=buy.ask,
            sell_price=sell.bid,
            dif=spread_percent,
            prof=profit,
            value=value,
            amount=amount,
            price=buy.ask,
            chain=self.default_chain,
            timestamp=timestamp,
        )

    async def scan_symbol(self, symbol: str) -> Optional[CexCexSignal]:
        quotes = await self.data_source.get_quotes(self.connectors, symbol)
        best_quotes = self._select_best_quotes(quotes)
        if not best_quotes:
            return None
        signal = self._build_signal(*best_quotes)
        if signal and signal.dif >= self.min_profit_percent:
            logger.info(
                "Opportunity %s: buy %s @ %.4f, sell %s @ %.4f | dif %.2f%% | value %.2f | prof %.2f",
                symbol,
                signal.buy_exchange,
                signal.buy_price,
                signal.sell_exchange,
                signal.sell_price,
                signal.dif,
                signal.value,
                signal.prof,
            )
            return signal
        return None

    async def scan_many(self, symbols: Iterable[str]) -> List[CexCexSignal]:
        tasks = [self.scan_symbol(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks)
        return [result for result in results if result]

    def scan_symbol_blocking(self, symbol: str) -> Optional[CexCexSignal]:
        return asyncio.run(self.scan_symbol(symbol))

    def scan_many_blocking(self, symbols: Iterable[str]) -> List[CexCexSignal]:
        return asyncio.run(self.scan_many(symbols))
