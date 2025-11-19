"""Standalone Hummingbot data source for CEX order books."""
from __future__ import annotations

import asyncio
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple, Type

from hummingbot.connector.exchange.binance.binance_exchange import BinanceExchange
from hummingbot.connector.exchange_base import ExchangeBase
from hummingbot.core.utils.async_utils import safe_ensure_future

from project.core.models.orderbook import OrderBookEntry, OrderBookSnapshot, build_entries


class HummingbotCexDataSource:
    """Lightweight wrapper around standalone Hummingbot connectors."""

    def __init__(self) -> None:
        self._exchange_map: Mapping[str, Type[ExchangeBase]] = {
            "binance": BinanceExchange,
        }
        self._connectors: Dict[Tuple[str, str], ExchangeBase] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    async def _ensure_connector(self, exchange: str, trading_pair: str) -> ExchangeBase:
        key = (exchange, trading_pair)
        if key in self._connectors:
            return self._connectors[key]
        if exchange not in self._exchange_map:
            raise ValueError(f"Exchange '{exchange}' is not configured.")

        lock = self._locks.setdefault(exchange, asyncio.Lock())
        async with lock:
            if key in self._connectors:
                return self._connectors[key]
            connector_cls = self._exchange_map[exchange]
            connector = connector_cls(
                client_config_map=None,
                connector_name=exchange,
                trading_pairs=[trading_pair],
            )
            await connector.start_network()
            await asyncio.sleep(1)
            safe_ensure_future(connector._order_book_tracker.start())
            await asyncio.sleep(1)
            self._connectors[key] = connector
            return connector

    async def fetch_snapshot(self, exchange: str, trading_pair: str) -> OrderBookSnapshot:
        """Return an order book snapshot for a given exchange/pair."""
        connector = await self._ensure_connector(exchange, trading_pair)
        order_book = connector.order_book_tracker.order_books.get(trading_pair)
        if order_book is None:
            raise RuntimeError(f"Order book not ready for {exchange}:{trading_pair}")
        bids = build_entries(order_book.bid_entries())
        asks = build_entries(order_book.ask_entries())
        return OrderBookSnapshot(trading_pair, bids, asks)

    async def best_prices(self, exchange: str, trading_pair: str) -> Tuple[float, float]:
        snapshot = await self.fetch_snapshot(exchange, trading_pair)
        return snapshot.best_bid(), snapshot.best_ask()

    async def vwap(self, exchange: str, trading_pair: str, side: str, quote_value: float) -> float:
        snapshot = await self.fetch_snapshot(exchange, trading_pair)
        return snapshot.vwap_price(side, quote_value)

    async def gather_best_prices(
        self,
        exchanges: Iterable[str],
        trading_pair: str,
    ) -> Dict[str, Tuple[float, float]]:
        """Fetch best bid/ask for multiple exchanges concurrently."""
        tasks = [self.best_prices(exc, trading_pair) for exc in exchanges]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        data: Dict[str, Tuple[float, float]] = {}
        for exchange, result in zip(exchanges, results):
            if isinstance(result, Exception):
                continue
            data[exchange] = result
        return data

