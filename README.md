## Web - UI
Человеческий интерфейс симулятора. Работает по адресу `localhost:8020` открывает главное меню с выбором интерфейса.

- `localhost:8020/admin` - интерфейс админ-панели симуляции.
- `localhost:8020/trader` - интерфейс трейдера
- `localhost:8020/docs` - документация API

## Руководство по эксплуатации Remote-Клиента

Клиент `TradingClient` оборачивает api-запросы в функции для простоты использования. 

Исходный файл клиента : `remote_client/trading_client.py`. Скопируйте его в свой проект и импортируйте из него класс клиента для использования.

В качестве примера представлен файл `remote_client/example.py`, в котором продемонстрировано использование всего функционала клиента.

### Требования


Для работы клиента необходима библиотека `requests`. 

### 1. Подключение и инициализация

Клиент инициализируется базовым URL сервера и вашим именем пользователя. Зарегистрированные пользователи указаны в конфиг-файле `config/start_config.json`. Использование незарегистрированного пользователя наделяет только правами наблюдатиеля.

* **Торговый режим**: Если передан валидный `username`, вы можете совершать сделки и запрашивать приватную статистику счёта.

* **Режим Наблюдателя**: Если указать несуществующий аккаунт, клиент сможет только читать публичные данные рынка (цены, события, индекс).

Пример использования :
```python
from trading_client import TradingClient

# ========CONFIG=========
connection_url = "http://localhost:8020"

# Если username указан, клиент работает как трейдер. Если None — только как наблюдатель.
client = TradingClient(base_url=connection_url, username="TradingBot")

def main():
    # Получить данные о рынке
    market_status = client.get_market_status()
    
    # Получить данные о индексе
    index_data = client.get_market_index()
    
    # Получить список компаний и их текущие цены
    companies = client.get_companies()
    
    #Тестовый тикер
    test_ticker = "PWR"
    
    # Получить историю цен для тестового тикера
    history = client.get_price_history(ticker=test_ticker, limit=5)
    
    # Получить фундаментальные данные для тестового тикера
    fundamentals = client.get_fundamentals(ticker=test_ticker)
    
    events = client.get_events()

    # Получить техническиеданные о брокере
    broker_status = client.get_broker_status()
    
    # Получить данные о ликвидациях
    liquidations = client.get_liquidations()
    
    # Получить информацию о счете
    account_info = client.get_account_info()

    # Получить текущую цену тестового тикера
    current_price  = client.get_current_price(test_ticker)

    # Получить текущее количество свободных средств на счете
    cash = client.get_cash_balance()

    # Получить текущую стоимость портфеля
    value = client.get_portfolio_value()

    # Получить текущий уровень маржи (UDS)
    uds = client.get_uds()

    # Проверить, находится ли счет в безопасности от маржин-колла
    sefty = client.is_healthy()

    # Попытаться купить акции
    buy_res = client.buy(ticker=test_ticker, quantity=10)

    # Получить информацию о позиции по тестовому тикеру
    position = client.get_position(ticker=test_ticker)

    # Попытаться продать акции
    sell_res = client.sell(ticker=test_ticker, quantity=5)

    # Альтернативный способ выполнения ордера
    exec_res = client.execute_order(ticker=test_ticker, action="SELL", quantity=5)

    # Получить историю ордеров
    orders = client.get_order_history(limit=5)

if __name__ == "__main__":
    main()
```
