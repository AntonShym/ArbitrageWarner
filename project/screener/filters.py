"""Filter utilities for signals."""
from __future__ import annotations

from typing import Iterable, List

from project.core.models.signal import ArbitrageSignal


def min_difference(signals: Iterable[ArbitrageSignal], threshold: float) -> List[ArbitrageSignal]:
    return [signal for signal in signals if signal.rows and signal.rows[-1].dif >= threshold]

