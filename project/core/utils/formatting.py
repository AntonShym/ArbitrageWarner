"""Formatting helpers for Telegram-friendly messages."""
from __future__ import annotations

from typing import Iterable, List, Sequence


def format_percent(value: float, precision: int = 1) -> str:
    return f"{value:.{precision}f}%"


def format_currency(value: float, precision: int = 2, suffix: str = "$") -> str:
    return f"{value:.{precision}f}{suffix}"


def format_amount(value: float, precision: int = 6) -> str:
    return f"{value:.{precision}f}"


def align_table(rows: Sequence[Sequence[str]]) -> List[str]:
    """Align cells into padded table rows."""
    if not rows:
        return []
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    aligned = []
    for row in rows:
        padded = [col.ljust(widths[idx]) for idx, col in enumerate(row)]
        aligned.append(" | ".join(padded))
    return aligned


def render_table(header: Iterable[str], rows: Iterable[Iterable[str]]) -> str:
    data = [list(header), ["-" * len(col) for col in header]]
    data.extend([list(row) for row in rows])
    lines = align_table(data)
    return "\n".join(lines)

