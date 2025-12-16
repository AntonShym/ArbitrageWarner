from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

import yaml


@dataclass
class ScannerConfig:
    symbols: List[str]
    exchanges: List[str]
    min_profit_percent: float
    notional: float
    classification: dict
    timeouts: dict


def load_config(path: Path) -> ScannerConfig:
    raw = yaml.safe_load(path.read_text())
    return ScannerConfig(
        symbols=raw["symbols"],
        exchanges=raw["exchanges"],
        min_profit_percent=float(raw["min_profit_percent"]),
        notional=float(raw["notional"]),
        classification=raw["classification"],
        timeouts=raw["timeouts"],
    )
