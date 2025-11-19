"""Mathematical helpers for arbitrage calculations."""
from __future__ import annotations

from typing import Sequence


def calculate_dif(buy_price: float, sell_price: float) -> float:
    if buy_price <= 0:
        return 0.0
    return (sell_price - buy_price) / buy_price * 100


def calculate_profit(buy_price: float, sell_price: float, amount: float) -> float:
    return max(0.0, sell_price - buy_price) * amount


def vwap_from_levels(levels: Sequence[tuple], amount: float) -> float:
    remaining = amount
    total_cost = 0.0
    total_converted = 0.0

    for price, level_amount in levels:
        if remaining <= 0:
            break
        take_amount = min(level_amount, remaining)
        total_cost += take_amount * price
        total_converted += take_amount
        remaining -= take_amount

    if remaining > 0 or total_converted <= 0:
        raise RuntimeError("Not enough liquidity")
    return total_cost / total_converted

