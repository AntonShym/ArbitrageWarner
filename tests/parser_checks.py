from __future__ import annotations

import logging
from pathlib import Path

from core.data_sources.quants_cex import QuantsLabCEXDataSource
from core.utils.config_loader import load_config
from core.utils.logger import setup_logging

logger = logging.getLogger(__name__)


def run_parser_checks() -> None:
    root = Path(__file__).resolve().parents[1]
    config = load_config(root / "config.yaml")
    data_source = QuantsLabCEXDataSource(config.exchanges)

    for symbol in config.symbols:
        snapshots = data_source.fetch_many(symbol)
        for exchange in config.exchanges:
            snapshot = snapshots.get(exchange)
            if snapshot is None:
                logger.warning("[MISS] %s %s bid/ask unavailable", exchange, symbol)
            else:
                logger.info(
                    "[OK] %s %s bid=%.6f ask=%.6f", 
                    exchange,
                    symbol,
                    snapshot.bid,
                    snapshot.ask,
                )


if __name__ == "__main__":
    setup_logging()
    run_parser_checks()
