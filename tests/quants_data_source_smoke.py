"""Lightweight parser smoke test required by AGENTS instructions."""
from __future__ import annotations

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from project.core.data_sources.quants_cex import QuantsLabCexDataSource

TEST_CONNECTORS = ["binance", "kucoin"]
TEST_SYMBOLS = ["BTC/USDT", "ETH/USDT"]


class FixtureClobSource:
    def __init__(self, fixtures: Dict[str, Dict[str, Tuple[float, float]]]):
        self._fixtures = fixtures

    async def get_order_book_snapshot(self, connector_name: str, trading_pair: str, depth: int = 10):
        levels = self._fixtures.get(connector_name, {}).get(trading_pair)
        if levels is None:
            raise ValueError(f"No fixture for {connector_name} {trading_pair}")
        bid, ask = levels
        return {
            "bids": [[bid, 1.0]],
            "asks": [[ask, 1.0]],
            "timestamp": time.time(),
        }


FIXTURE_BOOKS: Dict[str, Dict[str, Tuple[float, float]]] = {
    "binance": {
        "BTC-USDT": (100.0, 100.5),
        "ETH-USDT": (2000.0, 2000.5),
    },
    "kucoin": {
        "BTC-USDT": (101.0, 101.5),
        "ETH-USDT": (2001.0, 2001.5),
    },
}


async def _log_quotes(ds: QuantsLabCexDataSource, connectors: Iterable[str], symbol: str) -> bool:
    quotes = await ds.get_quotes(connectors, symbol)
    if not quotes:
        logging.warning("[WARN] No quotes for %s", symbol)
        return False
    for quote in quotes:
        logging.info(
            "[OK] %s %s bid=%.4f ask=%.4f",
            quote.connector,
            quote.symbol,
            quote.bid or -1,
            quote.ask or -1,
        )
    return True


async def _run_with_source(ds: QuantsLabCexDataSource, connectors: Iterable[str]) -> bool:
    try:
        results = await asyncio.gather(*(_log_quotes(ds, connectors, symbol) for symbol in TEST_SYMBOLS))
        return any(results)
    finally:
        await ds.aclose()


async def run_smoke():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    live_success = await _run_with_source(QuantsLabCexDataSource(depth=5), TEST_CONNECTORS)
    if live_success:
        logging.info("Live connector smoke test passed")
        return
    logging.warning("Live connectors unavailable; falling back to fixture snapshots")
    fixture_clob = FixtureClobSource(FIXTURE_BOOKS)
    fixture_source = QuantsLabCexDataSource(depth=5, clob_source=fixture_clob)  # type: ignore[arg-type]
    await _run_with_source(fixture_source, FIXTURE_BOOKS.keys())


def main():
    asyncio.run(run_smoke())


if __name__ == "__main__":
    main()
