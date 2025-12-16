from __future__ import annotations

import importlib
import logging
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, Mapping, Optional

from core.models.signals import SpreadSnapshot

logger = logging.getLogger(__name__)

TickerFactory = Callable[..., Any]


class QuantsLabCEXDataSource:
    """Fetches bid/ask information exclusively via quants-lab."""

    def __init__(
        self,
        exchanges: Iterable[str],
        factory: Optional[TickerFactory] = None,
    ) -> None:
        self._exchange_ids = list(exchanges)
        self._factory = factory or self._resolve_quants_lab_factory()
        self._clients = self._bootstrap_clients()

    def _resolve_quants_lab_factory(self) -> TickerFactory:
        """Imports the quants-lab CLOB data source or raises an error."""

        module_candidates = [
            "hummingbot.quants_lab.data_sources.cex.clob_data_source",
            "quants_lab.data_sources.cex.clob_data_source",
        ]
        for module_name in module_candidates:
            try:
                module = importlib.import_module(module_name)
                factory = getattr(module, "CLOBDataSource", None)
                if factory is not None:
                    logger.info("Using quants-lab data source from %s", module_name)
                    return factory
            except ModuleNotFoundError:
                continue
        raise RuntimeError(
            "quants-lab package is not available. Install it from "
            "https://github.com/hummingbot/quants-lab before running the screener."
        )

    def _bootstrap_clients(self) -> Dict[str, Any]:
        clients: Dict[str, Any] = {}
        for exchange_id in self._exchange_ids:
            clients[exchange_id] = self._factory(exchange=exchange_id)
        return clients

    def fetch_snapshot(self, exchange_id: str, symbol: str) -> Optional[SpreadSnapshot]:
        client = self._clients.get(exchange_id)
        if client is None:
            raise ValueError(f"Exchange '{exchange_id}' is not configured")

        ticker = client.get_ticker(symbol)
        bid = self._extract_price(ticker, ("best_bid", "bid"))
        ask = self._extract_price(ticker, ("best_ask", "ask"))

        if bid is None or ask is None:
            logger.warning(
                "Ticker for %s on %s does not include bid/ask values", symbol, exchange_id
            )
            return None

        return SpreadSnapshot(
            symbol=symbol,
            exchange=exchange_id,
            bid=float(bid),
            ask=float(ask),
            timestamp=datetime.utcnow(),
        )

    def fetch_many(self, symbol: str) -> Dict[str, SpreadSnapshot]:
        snapshots: Dict[str, SpreadSnapshot] = {}
        for exchange_id in self._exchange_ids:
            snapshot = self.fetch_snapshot(exchange_id, symbol)
            if snapshot is not None:
                snapshots[exchange_id] = snapshot
        return snapshots

    @staticmethod
    def _extract_price(ticker: Any, candidates: Iterable[str]) -> Optional[float]:
        for key in candidates:
            value = None
            if isinstance(ticker, Mapping) and key in ticker:
                value = ticker[key]
            elif hasattr(ticker, key):
                value = getattr(ticker, key)
            if value is not None:
                return float(value)
        return None
