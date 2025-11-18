"""Entry point for quick manual checks of CEX-CEX spreads."""
from __future__ import annotations

import argparse
import asyncio
import logging
from typing import List

from project.screener.cex_cex import CexCexArbitrageScreener

DEFAULT_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
DEFAULT_CONNECTORS = [
    "binance",
    "kucoin",
    "gate_io",
    "bybit",
]
DEFAULT_MIN_PROFIT = 0.5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simple CEX-CEX arbitrage scanner")
    parser.add_argument("--symbols", nargs="*", default=DEFAULT_SYMBOLS,
                        help="Trading pairs to scan in BASE/QUOTE format")
    parser.add_argument("--connectors", nargs="*", default=DEFAULT_CONNECTORS,
                        help="quants-lab connector names (see hummingbot settings)")
    parser.add_argument("--min-profit", type=float, default=DEFAULT_MIN_PROFIT,
                        help="Minimum spread percent required to report an opportunity")
    return parser.parse_args()


async def run_scan(symbols: List[str], connectors: List[str], min_profit: float):
    screener = CexCexArbitrageScreener(connectors, min_profit)
    opportunities = await screener.scan_many(symbols)
    if not opportunities:
        logging.info("No opportunities above %.2f%%", min_profit)
        return
    for opp in opportunities:
        logging.info(
            "🚨 %s | Buy %s @ %.4f → Sell %s @ %.4f | Spread %.2f%%",
            opp.symbol,
            opp.buy_exchange,
            opp.buy_price,
            opp.sell_exchange,
            opp.sell_price,
            opp.spread_percent,
        )


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    args = parse_args()
    asyncio.run(run_scan(args.symbols, args.connectors, args.min_profit))


if __name__ == "__main__":
    main()
