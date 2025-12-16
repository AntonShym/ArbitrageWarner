from __future__ import annotations

from core.models.signals import CexCexSignal


class MessageBuilder:
    """Converts structured signals into Telegram-friendly text."""

    def build_cex_cex(self, signal: CexCexSignal) -> str:
        lines = [
            "🚨 Сигнал CEX → CEX",
            f"Монета: {signal.symbol}",
            f"Классификация: {signal.classification.upper()}",
            f"Купить: {signal.buy_exchange} @ {signal.buy_price:.4f}",
            f"Продать: {signal.sell_exchange} @ {signal.sell_price:.4f}",
            f"dif: {signal.dif:.2f}% | prof: {signal.profit:.2f}$",
            f"value: {signal.value:.2f}$ | amount: {signal.amount:.6f}",
        ]
        if signal.chain:
            lines.append(f"chain: {signal.chain}")
        return "\n".join(lines)
