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
DEFAULT_TARGET_VALUE = 1000.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simple CEX-CEX arbitrage scanner")
    parser.add_argument("--symbols", nargs="*", default=DEFAULT_SYMBOLS,
                        help="Trading pairs to scan in BASE/QUOTE format")
    parser.add_argument("--connectors", nargs="*", default=DEFAULT_CONNECTORS,
                        help="quants-lab connector names (see hummingbot settings)")
    parser.add_argument("--min-profit", type=float, default=DEFAULT_MIN_PROFIT,
                        help="Minimum spread percent required to report an opportunity")
    parser.add_argument("--target-value", type=float, default=DEFAULT_TARGET_VALUE,
                        help="Quote currency notional (USD) used to estimate profit")
    return parser.parse_args()


async def run_scan(symbols: List[str], connectors: List[str], min_profit: float, target_value: float):
    screener = CexCexArbitrageScreener(connectors, min_profit, target_value=target_value)
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
            opp.dif,
        )
        logging.info(
            "Notional %.2f, amount %.6f, profit %.2f USD",
            opp.value,
            opp.amount,
            opp.prof,
        )


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    args = parse_args()
    asyncio.run(run_scan(args.symbols, args.connectors, args.min_profit, args.target_value))


if __name__ == "__main__":
    main()
