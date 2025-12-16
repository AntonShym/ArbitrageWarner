from __future__ import annotations

import time
from typing import Dict, Tuple

from core.models.signals import CexCexSignal


class SignalStateTracker:
    """Keeps track of recently emitted signals to avoid spamming duplicates."""

    def __init__(self, lifetime_seconds: float):
        self._lifetime = lifetime_seconds
        self._last_seen: Dict[Tuple[str, str, str], float] = {}

    def should_emit(self, signal: CexCexSignal) -> bool:
        now = time.time()
        identity = signal.identity_key()
        last_seen = self._last_seen.get(identity)
        if last_seen is not None and now - last_seen < self._lifetime:
            return False
        self._last_seen[identity] = now
        return True
