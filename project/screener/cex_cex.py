"""CEX-CEX arbitrage logic built on top of quants-lab data."""
from __future__ import annotations

import asyncio
import logging
from typing import Iterable, List, Optional

from project.core.data_sources.quants_cex import QuantsLabCexDataSource
from project.core.models.quotes import CexArbitrageOpportunity, CexQuote

logger = logging.getLogger(__name__)


class CexCexArbitrageScreener:
    """Scans multiple connectors for profitable spreads."""

    def __init__(
        self,
        connectors: Iterable[str],
        min_profit_percent: float,
        data_source: Optional[QuantsLabCexDataSource] = None,
    ):
        self.connectors = list(connectors)
        self.min_profit_percent = min_profit_percent
        self.data_source = data_source or QuantsLabCexDataSource()

    @staticmethod
    def _pick_best(quotes: List[CexQuote]) -> Optional[CexArbitrageOpportunity]:
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

        spread_percent = ((best_sell.bid - best_buy.ask) / best_buy.ask) * 100
        if spread_percent < 0:
            return None

        return CexArbitrageOpportunity(
            symbol=best_buy.symbol,
            buy_exchange=best_buy.connector,
            sell_exchange=best_sell.connector,
            buy_price=best_buy.ask,
            sell_price=best_sell.bid,
            spread_percent=spread_percent,
        )

    async def scan_symbol(self, symbol: str) -> Optional[CexArbitrageOpportunity]:
        quotes = await self.data_source.get_quotes(self.connectors, symbol)
        opportunity = self._pick_best(quotes)
        if opportunity and opportunity.spread_percent >= self.min_profit_percent:
            logger.info(
                "Opportunity for %s: buy on %s @ %.4f, sell on %s @ %.4f (%.2f%%)",
                symbol,
                opportunity.buy_exchange,
                opportunity.buy_price,
                opportunity.sell_exchange,
                opportunity.sell_price,
                opportunity.spread_percent,
            )
            return opportunity
        return None

    async def scan_many(self, symbols: Iterable[str]) -> List[CexArbitrageOpportunity]:
        tasks = [self.scan_symbol(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks)
        return [result for result in results if result]

    def scan_symbol_blocking(self, symbol: str) -> Optional[CexArbitrageOpportunity]:
        return asyncio.run(self.scan_symbol(symbol))

    def scan_many_blocking(self, symbols: Iterable[str]) -> List[CexArbitrageOpportunity]:
        return asyncio.run(self.scan_many(symbols))
