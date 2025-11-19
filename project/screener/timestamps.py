"""Signal lifetime and deduplication logic."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from project.core.models.signal import ArbitrageSignal
from project.core.utils.time import lifetime_seconds, utc_timestamp


@dataclass
class SignalTracker:
    timeout_sec: float
    storage: Dict[str, float] = field(default_factory=dict)
    first_seen: Dict[str, float] = field(default_factory=dict)

    def should_emit(self, signal: ArbitrageSignal) -> bool:
        identity = signal.identity()
        now = utc_timestamp()
        first = self.first_seen.setdefault(identity, now)
        last_sent = self.storage.get(identity)
        signal.lifetime_sec = lifetime_seconds(first, now)
        if last_sent and (now - last_sent) < self.timeout_sec:
            return False
        self.storage[identity] = now
        return True

