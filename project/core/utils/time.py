"""Time helper utilities."""
from __future__ import annotations

import time


def utc_timestamp() -> float:
    return time.time()


def lifetime_seconds(first_seen: float, current: float) -> float:
    return max(0.0, current - first_seen)

