"""CEX -> DEX arbitrage detection."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from project.core.data_sources.hb_cex import HummingbotCexDataSource
from project.core.data_sources.hb_dex import DexQuoteProvider
from project.core.models.signal import ArbitrageSignal, SignalRow
from project.core.utils.math import calculate_dif, calculate_profit
from project.core.utils.time import utc_timestamp
from project.screener.classify import classify_signal
from project.screener.contract_validator import validate_contracts


@dataclass
class CexDexConfig:
    exchange: str
    trading_pair: str
    dex_buy_token: str
    dex_sell_token: str
    dex_api: str
    min_difference: float
    target_value: float
    cex_contract: Optional[str] = None
    dex_contract: Optional[str] = None


class CexDexScreener:
    """Signal builder for sending volume from CEX to DEX."""

    def __init__(
        self,
        config: CexDexConfig,
        cex_source: Optional[HummingbotCexDataSource] = None,
        dex_provider: Optional[DexQuoteProvider] = None,
    ) -> None:
        self.config = config
        self.cex_source = cex_source or HummingbotCexDataSource()
        self.dex_provider = dex_provider or DexQuoteProvider(config.dex_api)

    async def scan(self) -> Optional[ArbitrageSignal]:
        _, best_ask = await self.cex_source.best_prices(self.config.exchange, self.config.trading_pair)
        dex_quote = await self.dex_provider.fetch_quote(
            buy_token=self.config.dex_buy_token,
            sell_token=self.config.dex_sell_token,
            sell_amount=self.config.target_value,
        )
        dif = calculate_dif(best_ask, dex_quote.price)
        if dif < self.config.min_difference:
            return None
        amount = self.config.target_value / best_ask
        profit = calculate_profit(best_ask, dex_quote.price, amount)
        valid, note = validate_contracts(self.config.cex_contract, self.config.dex_contract)
        if not valid:
            return None
        rows = [
            SignalRow(self.config.exchange, -dif, -profit, self.config.target_value, best_ask, chain=None),
            SignalRow("DEX", dif, profit, self.config.target_value, dex_quote.price, chain=note),
        ]
        base, quote = self.config.trading_pair.split("-")
        return ArbitrageSignal(
            pair=self.config.trading_pair,
            base=base,
            quote=quote,
            signal_type="cex_dex",
            direction=f"{self.config.exchange} -> DEX",
            sell_price=dex_quote.price,
            amount=amount,
            value=self.config.target_value,
            value_max=self.config.target_value,
            rows=rows,
            classification=classify_signal(dif),
            timestamp=utc_timestamp(),
        )

