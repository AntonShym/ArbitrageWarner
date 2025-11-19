"""Entrypoint for ArbitrageWarner scanners."""
from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path
from typing import Dict, List

import yaml

from project.screener.cex_cex import CexCexScreener, CexMarketConfig
from project.screener.message_builder import build_message
from project.screener.timestamps import SignalTracker


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ArbitrageWarner")
    parser.add_argument("--config", default="config.yaml", help="Path to YAML configuration file")
    return parser.parse_args()


def load_config(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


async def run_cex_cex(config: Dict) -> List[str]:
    markets = [CexMarketConfig(**market) for market in config.get("markets", [])]
    trading_pairs = sorted({market.trading_pair for market in markets})
    screener = CexCexScreener(
        markets=markets,
        min_difference=config.get("min_difference", 1.0),
        target_value=config.get("target_value", 1000.0),
    )
    tracker = SignalTracker(timeout_sec=config.get("timeout_sec", 60))
    signals = await screener.scan(trading_pairs)
    messages: List[str] = []
    for signal in signals:
        if tracker.should_emit(signal):
            messages.append(build_message(signal))
    return messages


async def run_all(config: Dict) -> None:
    cex_config = config.get("cex", {})
    messages = await run_cex_cex(
        {
            "markets": cex_config.get("markets", []),
            "min_difference": cex_config.get("min_difference", 1.0),
            "target_value": cex_config.get("target_value", 1000.0),
            "timeout_sec": config.get("runtime", {}).get("timeout_sec", 60),
        }
    )
    for message in messages:
        logging.info("\n%s", message)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    args = parse_args()
    config_path = Path(args.config)
    config = load_config(config_path)
    asyncio.run(run_all(config))


if __name__ == "__main__":
    main()
