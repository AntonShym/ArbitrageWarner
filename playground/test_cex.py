import asyncio
from project.core.data_sources.hb_cex import HBCEXDataSource


async def main():
    ds = HBCEXDataSource("binance", "BTC-USDT")
    print("Connecting...")
    await ds.connect()
    print("Connected!")

    print("Waiting a moment for live OB...")
    await asyncio.sleep(3)

    best = await ds.get_best_bid_ask()
    print("Best bid/ask:", best)

    vwap = await ds.get_vwap_price("buy", 1000)
    print("VWAP buy price for $1000:", vwap)


asyncio.run(main())
