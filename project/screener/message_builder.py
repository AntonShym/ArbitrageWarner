"""Telegram-ready message builder."""
from __future__ import annotations

from typing import Iterable, List, Sequence

from project.core.models.signal import ArbitrageSignal, SignalRow
from project.core.utils.formatting import (
    align_table,
    format_amount,
    format_currency,
    format_percent,
)


def _table_rows(rows: Sequence[SignalRow]) -> List[List[str]]:
    formatted = []
    for row in rows:
        formatted.append([
            row.exc,
            format_percent(row.dif),
            format_currency(row.prof),
            format_currency(row.value, suffix=""),
            f"{row.price:.6f}",
            row.chain or "",
        ])
    return formatted


def build_message(signal: ArbitrageSignal) -> str:
    header = f"{signal.pair} ({format_percent(signal.rows[-1].dif)})\n{signal.direction}"
    lines = [
        header,
        "",
        f"sell price: {format_currency(signal.sell_price)}",
        f"amount: {format_amount(signal.amount)}",
        f"value: {format_currency(signal.value)} (max {format_currency(signal.value_max)})",
        "",
    ]
    header_row = ["exc", "dif", "prof", "value", "price", "chain"]
    separator_row = ["-" * len(col) for col in header_row]
    table = [header_row, separator_row]
    table.extend(_table_rows(signal.rows))
    lines.extend(align_table(table))
    lines.append("")
    lines.append(f"Lifetime: {signal.lifetime_sec / 60:.1f} minutes")
    return "\n".join(lines)
