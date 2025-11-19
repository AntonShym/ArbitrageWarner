"""DEX -> CEX arbitrage detection."""
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
class DexCexConfig:
    exchange: str
    trading_pair: str
    dex_buy_token: str
    dex_sell_token: str
    dex_api: str
    min_difference: float
    target_value: float
    cex_contract: Optional[str] = None
    dex_contract: Optional[str] = None


class DexCexScreener:
    """Signal builder for selling on CEX after DEX fills."""

    def __init__(
        self,
        config: DexCexConfig,
        cex_source: Optional[HummingbotCexDataSource] = None,
        dex_provider: Optional[DexQuoteProvider] = None,
    ) -> None:
        self.config = config
        self.cex_source = cex_source or HummingbotCexDataSource()
        self.dex_provider = dex_provider or DexQuoteProvider(config.dex_api)

    async def scan(self) -> Optional[ArbitrageSignal]:
        best_bid, _ = await self.cex_source.best_prices(self.config.exchange, self.config.trading_pair)
        dex_quote = await self.dex_provider.fetch_quote(
            buy_token=self.config.dex_buy_token,
            sell_token=self.config.dex_sell_token,
            sell_amount=self.config.target_value,
        )
        dif = calculate_dif(dex_quote.price, best_bid)
        if dif < self.config.min_difference:
            return None
        amount = self.config.target_value / dex_quote.price
        profit = calculate_profit(dex_quote.price, best_bid, amount)
        valid, note = validate_contracts(self.config.cex_contract, self.config.dex_contract)
        if not valid:
            return None
        rows = [
            SignalRow(
                exc="DEX",
                dif=-dif,
                prof=-profit,
                value=self.config.target_value,
                price=dex_quote.price,
                chain=note,
            ),
            SignalRow(
                exc=self.config.exchange,
                dif=dif,
                prof=profit,
                value=self.config.target_value,
                price=best_bid,
            ),
        ]
        base, quote = self.config.trading_pair.split("-")
        return ArbitrageSignal(
            pair=self.config.trading_pair,
            base=base,
            quote=quote,
            signal_type="dex_cex",
            direction="DEX -> CEX",
            sell_price=best_bid,
            amount=amount,
            value=self.config.target_value,
            value_max=self.config.target_value,
            rows=rows,
            classification=classify_signal(dif),
            timestamp=utc_timestamp(),
        )
