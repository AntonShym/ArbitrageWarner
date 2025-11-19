"""Integration helpers that adapt quants-lab's CLOB data source to our project."""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from project.core.models.quotes import CexQuote
from project.quants_lab_adapters import QUANTS_LAB_PATH  # noqa: F401 - ensure quants-lab path is registered

from core.data_sources.clob import CLOBDataSource  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class OrderBookSnapshot:
    """Internal helper structure for normalised order book data."""

    bids: List[List[float]]
    asks: List[List[float]]
    timestamp: float

    @property
    def best_bid(self) -> Optional[float]:
        return float(self.bids[0][0]) if self.bids else None

    @property
    def best_ask(self) -> Optional[float]:
        return float(self.asks[0][0]) if self.asks else None


class QuantsLabCexDataSource:
    """Thin wrapper around quants-lab's ``CLOBDataSource`` that exposes best bid/ask quotes."""

    def __init__(
        self,
        depth: int = 5,
        clob_source: Optional[CLOBDataSource] = None,
    ):
        self._depth = depth
        self._clob = clob_source or CLOBDataSource()

    @staticmethod
    def _to_trading_pair(symbol: str) -> str:
        normalised = symbol.strip().upper().replace(" ", "")
        if "/" in normalised:
            base, quote = normalised.split("/", 1)
        elif "-" in normalised:
            base, quote = normalised.split("-", 1)
        else:
            return normalised
        return f"{base}-{quote}"

    def _normalise_levels(self, levels: List[Any]) -> List[List[float]]:
        normalised: List[List[float]] = []
        for raw_level in levels[: self._depth]:
            if len(raw_level) < 2:
                continue
            price, amount = raw_level[:2]
            try:
                normalised.append([float(price), float(amount)])
            except (TypeError, ValueError):
                continue
        return normalised

    def _to_snapshot(self, payload: Dict[str, Any]) -> Optional[OrderBookSnapshot]:
        bids = self._normalise_levels(payload.get("bids", []))
        asks = self._normalise_levels(payload.get("asks", []))
        if not bids and not asks:
            return None
        timestamp = float(payload.get("timestamp", time.time()))
        return OrderBookSnapshot(bids=bids, asks=asks, timestamp=timestamp)

    async def _fetch_snapshot(self, connector: str, symbol: str) -> Optional[OrderBookSnapshot]:
        trading_pair = self._to_trading_pair(symbol)
        try:
            payload = await self._clob.get_order_book_snapshot(connector, trading_pair, depth=self._depth)
        except Exception as exc:  # pragma: no cover - logging only
            logger.warning("Failed to fetch order book for %s on %s: %s", symbol, connector, exc)
            return None
        snapshot = self._to_snapshot(payload)
        if snapshot is None:
            logger.debug("Empty order book for %s on %s", symbol, connector)
        return snapshot

    async def get_quote(self, connector: str, symbol: str) -> Optional[CexQuote]:
        snapshot = await self._fetch_snapshot(connector, symbol)
        if snapshot is None:
            return None
        return CexQuote(
            connector=connector,
            symbol=symbol,
            bid=snapshot.best_bid,
            ask=snapshot.best_ask,
            timestamp=snapshot.timestamp,
        )

    async def get_quotes(self, connectors: Iterable[str], symbol: str) -> List[CexQuote]:
        tasks = [self.get_quote(connector, symbol) for connector in connectors]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        quotes: List[CexQuote] = []
        for connector, result in zip(connectors, results):
            if isinstance(result, Exception):  # pragma: no cover - logging only
                logger.error("Error loading quote from %s: %s", connector, result)
                continue
            if result:
                quotes.append(result)
            else:
                logger.debug("No quote for %s on %s", symbol, connector)
        return quotes

    async def aclose(self):
        """Hook for interface compatibility."""
        close = getattr(self._clob, "close", None)
        if callable(close):
            result = close()
            if asyncio.iscoroutine(result):
                await result

    def fetch_quotes_blocking(self, connectors: Iterable[str], symbol: str) -> List[CexQuote]:
        """Convenience wrapper that hides asyncio plumbing."""
        return asyncio.run(self.get_quotes(connectors, symbol))
