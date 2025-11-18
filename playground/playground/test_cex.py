import asyncio
from project.core.data_sources.hb_cex import HBCEXDataSource

async def main():
    # пример: бинанс, пара BTC-USDT
    ds = HBCEXDataSource("binance", "BTC-USDT")

    print("Connecting...")
    await ds.connect()
    print("Connected!")

    print("Waiting for orderbook snapshot...")
    await asyncio.sleep(3)

    # получить лучший bid/ask
    best = await ds.get_best_bid_ask()
    print("Best bid/ask:", best)

    # протестировать depth (например цена за покупку на 1000$)
    try:
        depth_price = await ds.get_depth("buy", 1000)
        print("VWAP buy price for 1000$:", depth_price)
    except Exception as e:
        print("Depth error:", e)

asyncio.run(main())
