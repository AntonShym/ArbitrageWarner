"""Lightweight HTTP-based DEX quote provider."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Dict, Optional

import aiohttp


@dataclass
class DexQuote:
    amount_in: float
    amount_out: float
    price: float
    gas: Optional[float] = None
    route: Optional[str] = None


class DexQuoteProvider:
    """Fetch swap quotes from aggregators like 0x."""

    def __init__(self, base_url: str, api_key: Optional[str] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session and not self._session.closed:
            return self._session
        async with self._session_lock:
            if self._session and not self._session.closed:
                return self._session
            self._session = aiohttp.ClientSession()
            return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def fetch_quote(
        self,
        buy_token: str,
        sell_token: str,
        sell_amount: float,
        params: Optional[Dict[str, str]] = None,
    ) -> DexQuote:
        session = await self._get_session()
        query = {"buyToken": buy_token, "sellToken": sell_token, "sellAmount": str(int(sell_amount))}
        if params:
            query.update(params)
        headers = {}
        if self.api_key:
            headers["0x-api-key"] = self.api_key
        async with session.get(f"{self.base_url}/swap/v1/quote", params=query, headers=headers) as resp:
            resp.raise_for_status()
            data = await resp.json()
            price = float(data["price"])
            return DexQuote(
                amount_in=float(data.get("sellAmount", sell_amount)),
                amount_out=float(data.get("buyAmount", 0)),
                price=price,
                gas=float(data.get("gasPrice", 0)),
                route=data.get("sources"),
            )

