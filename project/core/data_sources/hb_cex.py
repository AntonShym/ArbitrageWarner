# project/core/data_sources/hb_cex.py

import asyncio
from typing import Dict, Tuple, List

from hummingbot.connector.exchange.binance.binance_exchange import BinanceExchange
from hummingbot.core.utils.async_utils import safe_ensure_future


class HBCEXDataSource:
    """
    Minimal standalone Hummingbot connector wrapper.
    Works WITHOUT starting HummingbotApplication.

    Supports:
    - Live orderbook via websocket
    - Best bid/ask
    - VWAP depth quote
    """

    def __init__(self, exchange: str, trading_pair: str):
        """
        :param exchange: 'binance', 'okx', 'gate_io', etc.
        :param trading_pair: 'BTC-USDT'
        """
        self.exchange_name = exchange
        self.trading_pair = trading_pair

        # Connector instance (we create manually)
        self.connector = None

        # Maps exchange => class
        self.exchange_map = {
            "binance": BinanceExchange,
            # далее добавим другие биржи (okx, bybit, gate, bingx)
        }

        if exchange not in self.exchange_map:
            raise ValueError(f"Exchange '{exchange}' not implemented yet.")

    async def connect(self):
        """
        Initializes the connector and starts orderbook streams.
        """

        connector_class = self.exchange_map[self.exchange_name]

        self.connector = connector_class(
            client_config_map=None,         # not needed for read-only mode
            connector_name=self.exchange_name,
            trading_pairs=[self.trading_pair]
        )

        # Initialize websocket pipelines
        await self.connector.start_network()
        await asyncio.sleep(2)  # wait for websocket to connect

        # Start orderbook tracker
        safe_ensure_future(self.connector._order_book_tracker.start())
        await asyncio.sleep(2)

    async def get_best_bid_ask(self) -> Dict[str, float]:
        """
        Returns {'bid': ..., 'ask': ...}
        """
        ob = self.connector.order_book_tracker.order_books.get(self.trading_pair)
        if ob is None:
            raise RuntimeError("Orderbook not ready")

        return {
            "bid": ob.get_price("bid"),
            "ask": ob.get_price("ask"),
        }

    async def get_vwap_price(self, side: str, quote_volume: float) -> float:
        """
        :param side: "buy" or "sell"
        :param quote_volume: volume in QUOTE currency (e.g. 1000 USDT)
        :return: VWAP price
        """
        ob = self.connector.order_book_tracker.order_books.get(self.trading_pair)
        if ob is None:
            raise RuntimeError("Orderbook not ready")

        entries = ob.ask_entries() if side == "buy" else ob.bid_entries()

        remaining = quote_volume
        total_quote_cost = 0.0
        total_base_amount = 0.0

        for price, amount in entries:
            step_quote_value = price * amount

            if step_quote_value >= remaining:
                partial_base = remaining / price
                total_quote_cost += remaining
                total_base_amount += partial_base
                remaining = 0
                break

            remaining -= step_quote_value
            total_quote_cost += step_quote_value
            total_base_amount += amount

        if remaining > 0:
            raise RuntimeError(f"Not enough liquidity to fill {quote_volume}$")

        # VWAP = total quote spent / total base bought
        return total_quote_cost / total_base_amount
