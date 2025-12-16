from __future__ import annotations

from core.models.signals import CexCexSignal


def satisfies_min_profit(signal: CexCexSignal, min_profit_percent: float) -> bool:
    return signal.dif >= min_profit_percent
