import time
from trading_client import TradingClient

# ======== CONFIG =========
connection_url = "http://localhost:8020"

# Инициализируем клиента. 
# Если username указан, клиент работает как трейдер. Если None — только как наблюдатель.
client = TradingClient(base_url=connection_url, username="Admin")

def main():
    print("=== ДЕМОНСТРАЦИЯ РАБОТЫ TRADING CLIENT ===\n")

    # --- 1. ПУБЛИЧНЫЕ ДАННЫЕ РЫНКА (Market Engine API) ---
    print("--- 1.1 Статус рынка ---")
    market_status = client.get_market_status()
    print(f"Статус: {market_status}\n")

    print("--- 1.2 Рыночный индекс ---")
    index_data = client.get_market_index()
    print(f"Индекс: {index_data}\n")

    print("--- 1.3 Список компаний ---")
    companies = client.get_companies()
    
    test_ticker = "PWR"
    print(f"Доступные тикеры: {companies}\n")

    print(f"--- 1.4 История цен для {test_ticker} ---")
    history = client.get_price_history(ticker=test_ticker, limit=5)
    print(f"Последние 5 тиков: {history}\n")

    print(f"--- 1.5 Фундаментальные данные {test_ticker} ---")
    fundamentals = client.get_fundamentals(ticker=test_ticker)
    print(f"Фундаментал: {fundamentals}\n")

    print("--- 1.6 Активные события (Новости/Тренды) ---")
    events = client.get_events()
    print(f"События: {events}\n")


    # --- 2. ДАННЫЕ БРОКЕРА (Broker API) ---
    print("--- 2.1 Статус брокера ---")
    broker_status = client.get_broker_status()
    print(f"Брокер: {broker_status}\n")

    print("--- 2.2 Последние ликвидации (Маржин-коллы) ---")
    liquidations = client.get_liquidations()
    print(f"Ликвидированные счета: {liquidations}\n")


    # --- 3. ИНФОРМАЦИЯ О СЧЕТЕ И ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ---
    print(f"--- 3.1 Полная информация о счете '{client.username}' ---")
    account_info = client.get_account_info()
    # Выводим только ключи или часть данных, чтобы не засорять консоль
    if account_info:
        print(f"УДС: {account_info.get('uds')}, Балансы: {account_info.get('balances')}\n")
    else:
        print("Счет не найден или API недоступно.\n")

    print("--- 3.2 Вспомогательные метрики счета ---")
    print(f"Текущая цена {test_ticker}: {client.get_current_price(test_ticker)}")
    print(f"Свободный кэш: {client.get_cash_balance()}")
    print(f"Эквити (Оценка всего портфеля): {client.get_portfolio_value()}")
    print(f"Текущий УДС: {client.get_uds()}")
    print(f"Счет в безопасности (УДС > 0)? {client.is_healthy()}\n")


    # --- 4. ТОРГОВЛЯ ---
    print("--- 4.1 Торговые операции ---")
    
    # Метод buy()
    print(f"Попытка КУПИТЬ 10 акций {test_ticker}...")
    buy_res = client.buy(ticker=test_ticker, quantity=10)
    print(f"Результат: {buy_res}")

    time.sleep(1) # Симулируем небольшую паузу

    # Метод get_position()
    position = client.get_position(ticker=test_ticker)
    print(f"Текущая позиция по {test_ticker}: {position}")

    # Метод sell()
    print(f"Попытка ПРОДАТЬ 5 акций {test_ticker}...")
    sell_res = client.sell(ticker=test_ticker, quantity=5)
    print(f"Результат: {sell_res}")

    # Метод execute_order() (Универсальный, продаем оставшиеся 5 акций)
    print(f"Универсальный вызов: ПРОДАТЬ еще 5 акций {test_ticker}...")
    exec_res = client.execute_order(ticker=test_ticker, action="SELL", quantity=5)
    print(f"Результат: {exec_res}\n")

    print("--- 4.2 История ордеров ---")
    orders = client.get_order_history(limit=5)
    print(f"Последние 5 ордеров пользователя: {orders}\n")
    
    print("=== ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА ===")

if __name__ == "__main__":
    main()