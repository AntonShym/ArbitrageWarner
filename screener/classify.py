from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ClassificationThresholds:
    high: float
    medium: float


class SpreadClassifier:
    """Maps dif values to textual labels."""

    def __init__(self, thresholds: ClassificationThresholds):
        self._thresholds = thresholds

    def classify(self, dif_value: float) -> str:
        if dif_value >= self._thresholds.high:
            return "high"
        if dif_value >= self._thresholds.medium:
            return "medium"
        return "low"
