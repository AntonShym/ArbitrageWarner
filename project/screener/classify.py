"""Classification helpers."""
from __future__ import annotations


def classify_signal(dif: float) -> str:
    if dif >= 30:
        return "high"
    if dif >= 10:
        return "medium"
    if dif >= 1:
        return "low"
    return "ignore"

