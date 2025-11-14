import ccxt
# import time # Нам понадобится для задержки
# from telegram import Bot # Будем использовать позже

# --- Конфигурация сканера ---
SYMBOL = 'BTC/USDT'  # Можно использовать любой символ для теста
MIN_PROFIT_PERCENT = 0.5  # Минимальный спред, который нас интересует (0.5%)

# Биржи для сканирования 
EXCHANGE_CLASSES = [
    ccxt.binance,
    ccxt.kucoin,
    ccxt.gateio,
    ccxt.mexc,
    ccxt.bybit
    # Добавьте сюда остальные CEX из списка
]

def find_cex_cex_arbitrage(symbol):
    """
    Сканирует биржи для поиска арбитража CEX-CEX.
    """
    best_buy = {'price': float('inf'), 'exchange': None}
    best_sell = {'price': float('-inf'), 'exchange': None}
    
    # print(f"🔄 Сканирование {symbol}...")

    for ExchangeClass in EXCHANGE_CLASSES:
        exchange_name = ExchangeClass.id
        exchange = ExchangeClass({'enableRateLimit': True})
        
        try:
            ticker = exchange.fetch_ticker(symbol)
            
            # ask (Best Ask) - цена, по которой мы КУПИМ (на этой бирже)
            buy_price_here = ticker.get('ask') 
            # bid (Best Bid) - цена, по которой мы ПРОДАДИМ (на этой бирже)
            sell_price_here = ticker.get('bid')

            if buy_price_here is None or sell_price_here is None:
                continue

            # Ищем глобальные экстремумы
            if buy_price_here < best_buy['price']:
                best_buy['price'] = buy_price_here
                best_buy['exchange'] = exchange_name

            if sell_price_here > best_sell['price']:
                best_sell['price'] = sell_price_here
                best_sell['exchange'] = exchange_name
                
        except Exception:
            pass
            
    # Расчет спреда
    buy_at = best_buy['price']
    sell_at = best_sell['price']
    
    # Проверка на арбитраж и наличие данных
    if (buy_at == float('inf') or 
        sell_at == float('-inf') or 
        best_buy['exchange'] == best_sell['exchange']):
        return None

    raw_profit_percent = ((sell_at / buy_at) - 1) * 100

    if raw_profit_percent > MIN_PROFIT_PERCENT:
        return {
            'symbol': symbol,
            'buy': best_buy['exchange'],
            'buy_price': buy_at,
            'sell': best_sell['exchange'],
            'sell_price': sell_at,
            'profit': f"{raw_profit_percent:.2f}%"
        }
    
    return None

def main_loop():
    # Для теста просканируем 
    test_symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
    
    print("🤖 Запуск сканера CEX-CEX...")
    for s in test_symbols:
        result = find_cex_cex_arbitrage(s)
        
        if result:
            message = (
                f"🚨 СИГНАЛ АРБИТРАЖА CEX-CEX НАЙДЕН! 🚨\n"
                f"Монета: {result['symbol']} (Профит: {result['profit']})\n"
                f"КУПИТЬ на {result['buy']} по цене {result['buy_price']:.4f}\n"
                f"ПРОДАТЬ на {result['sell']} по цене {result['sell_price']:.4f}"
            )
            print(message)
            # Здесь будет код для отправки в Telegram
        # else:
            # print(f"✅ {s}: Спред меньше {MIN_PROFIT_PERCENT}%")
            
if __name__ == "__main__":
    main_loop()
