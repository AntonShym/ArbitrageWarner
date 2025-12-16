from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.data_sources.quants_cex import QuantsLabCEXDataSource
from core.models.signals import CexCexSignal, SpreadSnapshot
from screener.classify import SpreadClassifier


@dataclass
class ScannerStats:
    best_buy: SpreadSnapshot
    best_sell: SpreadSnapshot


class CexCexScanner:
    """Searches for cross-exchange spreads."""

    def __init__(
        self,
        data_source: QuantsLabCEXDataSource,
        classifier: SpreadClassifier,
        notional: float,
    ) -> None:
        self._data_source = data_source
        self._classifier = classifier
        self._notional = notional

    def scan_symbol(self, symbol: str) -> Optional[CexCexSignal]:
        snapshots = self._data_source.fetch_many(symbol)
        if len(snapshots) < 2:
            return None
        stats = self._find_best(snapshots)
        if stats is None:
            return None
        dif = ((stats.best_sell.bid / stats.best_buy.ask) - 1) * 100
        amount = self._notional / stats.best_buy.ask if stats.best_buy.ask else 0
        profit = self._notional * (dif / 100)
        classification = self._classifier.classify(dif)
        return CexCexSignal(
            symbol=symbol,
            buy_exchange=stats.best_buy.exchange,
            sell_exchange=stats.best_sell.exchange,
            buy_price=stats.best_buy.ask,
            sell_price=stats.best_sell.bid,
            dif=dif,
            profit=profit,
            value=self._notional,
            amount=amount,
            price=stats.best_buy.ask,
            classification=classification,
        )

    @staticmethod
    def _find_best(
        snapshots: dict[str, SpreadSnapshot]
    ) -> Optional[ScannerStats]:
        best_buy = None
        best_sell = None
        for snapshot in snapshots.values():
            if best_buy is None or snapshot.ask < best_buy.ask:
                best_buy = snapshot
            if best_sell is None or snapshot.bid > best_sell.bid:
                best_sell = snapshot
        if best_buy is None or best_sell is None:
            return None
        if best_buy.exchange == best_sell.exchange:
            return None
        return ScannerStats(best_buy=best_buy, best_sell=best_sell)
