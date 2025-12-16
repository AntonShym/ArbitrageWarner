from __future__ import annotations

import types
import unittest
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from core.data_sources.quants_cex import QuantsLabCEXDataSource


class DummyTicker:
    def __init__(self, bid: float, ask: float) -> None:
        self.best_bid = bid
        self.best_ask = ask


class DummyFactory:
    def __init__(self, ticker_map: Dict[str, Any]) -> None:
        self._ticker_map = ticker_map

    def __call__(self, exchange: str) -> Any:  # noqa: ANN401 - quants-lab client shape is dynamic
        client = MagicMock()
        client.get_ticker.side_effect = lambda symbol: self._ticker_map[(exchange, symbol)]
        return client


class QuantsLabCEXDataSourceTestCase(unittest.TestCase):
    def test_fetch_snapshot_returns_values_from_quants_lab(self) -> None:
        ticker = {"best_bid": 0.9, "best_ask": 1.1}
        factory = DummyFactory({("binance", "VRA/USDT"): ticker})
        data_source = QuantsLabCEXDataSource(["binance"], factory=factory)

        snapshot = data_source.fetch_snapshot("binance", "VRA/USDT")

        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertEqual(snapshot.bid, 0.9)
        self.assertEqual(snapshot.ask, 1.1)

    def test_fetch_snapshot_handles_attribute_payload(self) -> None:
        ticker = DummyTicker(0.1, 0.2)
        factory = DummyFactory({("okx", "BTC/USDT"): ticker})
        data_source = QuantsLabCEXDataSource(["okx"], factory=factory)

        snapshot = data_source.fetch_snapshot("okx", "BTC/USDT")

        self.assertEqual(snapshot.bid, 0.1)
        self.assertEqual(snapshot.ask, 0.2)

    def test_missing_quants_lab_package_raises_error(self) -> None:
        def _missing_import(_module: str) -> types.ModuleType:  # pragma: no cover - exercised by exception
            raise ModuleNotFoundError

        with patch("importlib.import_module", side_effect=_missing_import):
            with self.assertRaises(RuntimeError):
                QuantsLabCEXDataSource(["binance"])


if __name__ == "__main__":
    unittest.main()
