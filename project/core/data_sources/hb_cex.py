# project/core/data_sources/hb_cex.py

import asyncio
from typing import Dict, Any, Optional, List

from hummingbot.client.settings import AllConnectorSettings
from hummingbot.client.hummingbot_application import HummingbotApplication


class HBCEXDataSource:
    """
    Minimalistic Hummingbot-based CEX data source for arbitrage scanner.

    Only responsibilities:
    - Load connector
    - Pull best bid/ask
    - Pull orderbook depth
    - Give ability to compute effective price for volume
    """

    def __init__(self, exchange: str, trading_pair: str):
        """
        :param exchange: e.g., 'binance', 'bybit', 'okx'
        :param trading_pair: e.g., 'BTC-USDT'
        """
        self.exchange = exchange
        self.trading_pair = trading_pair
        self.connector = None
        self._app = None

    async def connect(self):
        """
        Loads and initializes connector through Hummingbot core.
        """
        self._app = HummingbotApplication.main_application()

        # Ensure connector exists in Hummingbot list
        if self.exchange not in AllConnectorSettings.get_connector_settings().keys():
            raise ValueError(f"Exchange '{self.exchange}' is not supported by Hummingbot.")

        # Load connector instance
        await self._app._initialize_connectors([self.exchange])

        self.connector = self._app.connectors.get(self.exchange)
        if self.connector is None:
            raise RuntimeError(f"Failed to load connector: {self.exchange}")

        # Subscribe to orderbook updates
        await self.connector.start_network()

    async def get_best_bid_ask(self) -> Dict[str, float]:
        """
        Returns best bid/ask for the trading pair.
        """
        ob = self.connector.order_book_tracker.order_books.get(self.trading_pair)
        if ob is None:
            raise RuntimeError(f"No orderbook for {self.exchange} {self.trading_pair}")

        best_bid = ob.get_price("bid")
        best_ask = ob.get_price("ask")

        return {
            "bid": best_bid,
            "ask": best_ask,
        }

    async def get_depth(self, side: str, volume_usd: float) -> float:
        """
        Computes volume-weighted average price (VWAP) for given USD value.

        :param side: 'buy' or 'sell'
        :param volume_usd: desired USD notional
        :return: average execution price for the whole volume
        """
        ob = self.connector.order_book_tracker.order_books.get(self.trading_pair)
        if ob is None:
            raise RuntimeError("Orderbook not available")

        side_book = ob.ask_entries() if side == "buy" else ob.bid_entries()

        remaining = volume_usd
        total_cost = 0.0

        for price, amount in side_book:
            step_value = amount * price
            if step_value >= remaining:
                total_cost += remaining
                remaining = 0
                break
            else:
                total_cost += step_value
                remaining -= step_value

        if remaining > 0:
            raise RuntimeError(f"Not enough liquidity on {self.exchange} to fill {volume_usd}$")

        avg_price = total_cost / (volume_usd / price)
        return avg_price

    async def get_networks(self) -> Optional[List[str]]:
        """
        Returns list of withdrawal networks (if supported by this connector).
        """
        try:
            info = await self.connector.get_account_balances()
            networks = list(info.get("networks", {}).keys())
            return networks
        except Exception:
            return None
