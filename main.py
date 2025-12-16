from __future__ import annotations

import logging
from pathlib import Path

from core.data_sources.quants_cex import QuantsLabCEXDataSource
from core.utils.config_loader import ScannerConfig, load_config
from core.utils.logger import setup_logging
from screener.cex_cex import CexCexScanner
from screener.classify import ClassificationThresholds, SpreadClassifier
from screener import filters
from screener.message_builder import MessageBuilder
from screener.timestamps import SignalStateTracker


def run_once(config: ScannerConfig) -> None:
    thresholds = ClassificationThresholds(
        high=config.classification["high"],
        medium=config.classification["medium"],
    )
    data_source = QuantsLabCEXDataSource(config.exchanges)
    classifier = SpreadClassifier(thresholds)
    scanner = CexCexScanner(data_source, classifier, config.notional)
    tracker = SignalStateTracker(config.timeouts["cex_cex_seconds"])
    builder = MessageBuilder()

    for symbol in config.symbols:
        try:
            signal = scanner.scan_symbol(symbol)
        except Exception:  # noqa: BLE001 - critical to keep scanner alive
            logging.exception("Failed to scan %s", symbol)
            continue
        if signal is None:
            continue
        if not filters.satisfies_min_profit(signal, config.min_profit_percent):
            continue
        if not tracker.should_emit(signal):
            continue
        message = builder.build_cex_cex(signal)
        print(message)


def main() -> None:
    setup_logging()
    config_path = Path(__file__).with_name("config.yaml")
    config = load_config(config_path)
    run_once(config)


if __name__ == "__main__":
    main()
