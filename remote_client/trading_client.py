import requests
import json
import time
from typing import Dict, List, Optional

class TradingClient:
    """
    Клиент для взаимодействия с API симуляции (Market Engine и Broker).
    """
    def __init__(self, base_url: str = connection_url, username: str = "TradingBot"):
        """
        Инициализация клиента.

        Входные данные:
            base_url (str): Базовый URL сервера симуляции.
            username (str): Имя пользователя (account) для выполнения торговых операций.

        Выходные данные:
            Объект TradingClient.
        """
        self.base_url = base_url
        self.username = username
        self.session = requests.Session()
    
    def get_companies(self) -> Dict:
        """
        Запрашивает список всех компаний, торгующихся на рынке, и их текущие котировки.

        Входные данные:
            Нет.

        Выходные данные:
            Dict: Словарь, содержащий данные компаний.
            Формат: {"companies": {"TICKER": {"price": float, "volatility": float, ...}, ...}}
            В случае ошибки возвращает пустой словарь {}.
        """
        try:
            resp = self.session.get(f"{self.base_url}/api/market/companies")
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"[ERROR] Ошибка получения компаний: {e}")
            return {}
    
    def get_price_history(self, ticker: str, limit: int = 100) -> List:
        """
        Получает историю цен для указанного тикера.

        Входные данные:
            ticker (str): Тикер компании (например, "AAPL").
            limit (int): Максимальное количество возвращаемых исторических свечей/тиков (по умолчанию 100).

        Выходные данные:
            List: Массив исторических данных цены.
            Формат: [{"tick": int, "price": float}, ...]
            В случае ошибки возвращает пустой список [].
        """
        try:
            resp = self.session.get(
                f"{self.base_url}/api/market/history/{ticker}",
                params={"limit": limit}
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("history", [])
        except requests.RequestException as e:
            print(f"[ERROR] Ошибка получения истории {ticker}: {e}")
            return []
    
    def get_fundamentals(self, ticker: str) -> Optional[Dict]:
        """
        Получает глубокую аналитику и фундаментальные данные по конкретной компании.

        Входные данные:
            ticker (str): Тикер компании.

        Выходные данные:
            Optional[Dict]: Словарь с фундаментальными показателями (базовая прибыль, дивиденды и т.д.).
            Возвращает None в случае ошибки.
        """
        try:
            resp = self.session.get(f"{self.base_url}/api/market/fundamentals/{ticker}")
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"[ERROR] Ошибка получения фундаментальных данных {ticker}: {e}")
            return None
    
    def get_market_index(self) -> Optional[Dict]:
        """
        Запрашивает текущее состояние рыночного индекса.

        Входные данные:
            Нет.

        Выходные данные:
            Optional[Dict]: Словарь с данными индекса (текущая цена, изменения за период).
            Возвращает None в случае ошибки.
        """
        try:
            resp = self.session.get(f"{self.base_url}/api/market/index")
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"[ERROR] Ошибка получения индекса: {e}")
            return None
    
    def get_market_status(self) -> Optional[Dict]:
        """
        Запрашивает системный статус Market Engine.

        Входные данные:
            Нет.

        Выходные данные:
            Optional[Dict]: Словарь со статусом рынка (номер текущего тика, цена индекса и т.д.).
            Возвращает None в случае ошибки.
        """
        try:
            resp = self.session.get(f"{self.base_url}/api/market/status")
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"[ERROR] Ошибка получения статуса рынка: {e}")
            return None
    
    def get_events(self) -> List[Dict]:
        """
        Читает список текущих новостей и активных событий, влияющих на рынок.

        Входные данные:
            Нет.

        Выходные данные:
            List[Dict]: Массив активных событий.
            Формат объекта в массиве: {"id": str, "name": str, "target": str, "impact_profit": float, ...}
            В случае ошибки возвращает пустой список [].
        """
        try:
            resp = self.session.get(f"{self.base_url}/api/market/events")
            resp.raise_for_status()
            data = resp.json()
            return data.get("events", [])
        except requests.RequestException as e:
            print(f"[ERROR] Ошибка получения событий: {e}")
            return []
    
    # ===== ИНФОРМАЦИЯ О СЧЁТЕ =====
    
    def get_account_info(self) -> Optional[Dict]:
        """
        Получает полную сводку по счёту текущего пользователя (баланс, позиции, маржа, УДС, PnL).

        Входные данные:
            Нет (использует self.username).

        Выходные данные:
            Optional[Dict]: Подробная информация о счёте согласно структуре AccountSummary.
            Формат:
            {
                "username": str,
                "uds": float,
                "uds_status": str,
                "balances": {"cash": float, "portfolio_value_current": float, ...},
                "margins": {"initial_margin": float, "min_margin": float},
                "pnl": {"daily_pnl": float, "total_return_percent": float, ...},
                "positions": [{"ticker": str, "quantity": int, "entry_price": float, "current_price": float, ...}, ...],
                "is_liquidated": bool
            }
            Возвращает None при ошибке.
        """
        try:
            resp = self.session.get(f"{self.base_url}/api/broker/account/{self.username}")
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"[ERROR] Ошибка получения информации о счёте: {e}")
            return None
    
    def get_order_history(self, limit: int = 50) -> List[Dict]:
        """
        Получает историю ордеров текущего пользователя.

        Входные данные:
            limit (int): Максимальное количество последних ордеров (по умолчанию 50).

        Выходные данные:
            List[Dict]: Массив истории ордеров (выполненных и отклонённых).
            Формат: [{"order_id": str, "ticker": str, "action": str, "quantity": int, "status": str, ...}, ...]
            При ошибке возвращает пустой список [].
        """
        try:
            resp = self.session.get(
                f"{self.base_url}/api/broker/order-history/{self.username}",
                params={"limit": limit}
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("orders", [])
        except requests.RequestException as e:
            print(f"[ERROR] Ошибка получения истории ордеров: {e}")
            return []
    
    def get_broker_status(self) -> Optional[Dict]:
        """
        Получает технический статус брокера (количество счетов, комиссий, ликвидаций).

        Входные данные:
            Нет.

        Выходные данные:
            Optional[Dict]: Словарь со статусом работы брокера.
            Формат: {"status": str, "total_accounts": int, "total_liquidated": int, ...}.
            Возвращает None в случае ошибки.
        """
        try:
            resp = self.session.get(f"{self.base_url}/api/broker/status")
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"[ERROR] Ошибка получения статуса брокера: {e}")
            return None
    
    def get_liquidations(self) -> List[Dict]:
        """
        Запрашивает список счетов, прошедших процедуру маржин-колла (ликвидации).

        Входные данные:
            Нет.

        Выходные данные:
            List[Dict]: Список ликвидированных счетов.
            Формат: [{"username": str, "cash_balance": float, "liquidation_info": dict}, ...].
            При ошибке возвращает пустой список [].
        """
        try:
            resp = self.session.get(f"{self.base_url}/api/broker/liquidations")
            resp.raise_for_status()
            data = resp.json()
            return data.get("accounts", [])
        except requests.RequestException as e:
            print(f"[ERROR] Ошибка получения ликвидаций: {e}")
            return []
    
    # ===== ТОРГОВЛЯ =====
    
    def execute_order(self, ticker: str, action: str, quantity: int) -> Optional[Dict]:
        """
        Универсальный метод отправки ордера на покупку или продажу актива.

        Входные данные:
            ticker (str): Тикер компании (например, "AAPL").
            action (str): Направление сделки - "BUY" или "SELL".
            quantity (int): Объем актива в лотах/штуках.

        Выходные данные:
            Optional[Dict]: Результат выполнения ордера согласно структуре OrderResponse.
            Формат:
            {
                "order_id": str,
                "status": str,  # "EXECUTED" или "REJECTED"
                "rejection_reason": str | None,
                "commission": float
            }
            Возвращает None при сетевой ошибке.
        """
        try:
            payload = {
                "username": self.username,
                "ticker": ticker,
                "action": action,
                "quantity": quantity
            }
            resp = self.session.post(
                f"{self.base_url}/api/broker/order",
                json=payload
            )
            resp.raise_for_status()
            result = resp.json()
            
            if result.get("status") == "EXECUTED":
                print(f"[INFO] Ордер выполнен: {action} {quantity} x {ticker}")
            else:
                print(f"[ERROR] Ордер отклонен: {result.get('rejection_reason', 'Неизвестная ошибка')}")
            
            return result
        except requests.RequestException as e:
            print(f"[ERROR] Ошибка выполнения ордера: {e}")
            return None
    
    def buy(self, ticker: str, quantity: int) -> Optional[Dict]:
        """
        Отправляет ордер на покупку актива.

        Входные данные:
            ticker (str): Тикер компании.
            quantity (int): Количество для покупки.

        Выходные данные:
            Optional[Dict]: Ответ сервера на отправленный ордер (см. execute_order).
        """
        return self.execute_order(ticker, "BUY", quantity)
    
    def sell(self, ticker: str, quantity: int) -> Optional[Dict]:
        """
        Отправляет ордер на продажу актива.

        Входные данные:
            ticker (str): Тикер компании.
            quantity (int): Количество для продажи.

        Выходные данные:
            Optional[Dict]: Ответ сервера на отправленный ордер (см. execute_order).
        """
        return self.execute_order(ticker, "SELL", quantity)
    
    # ===== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ =====
    
    def get_position(self, ticker: str) -> Optional[Dict]:
        """
        Извлекает информацию о конкретной позиции из портфеля пользователя.

        Входные данные:
            ticker (str): Тикер искомой компании.

        Выходные данные:
            Optional[Dict]: Данные о позиции.
            Формат: {"ticker": str, "quantity": int, "entry_price": float, "current_price": float, "position_value": float}.
            Если позиция отсутствует или произошла ошибка, возвращает None.
        """
        account = self.get_account_info()
        if account:
            for pos in account.get("positions", []):
                if pos["ticker"] == ticker:
                    return pos
        return None
    
    def get_current_price(self, ticker: str) -> Optional[float]:
        """
        Получает текущую рыночную стоимость конкретного актива.

        Входные данные:
            ticker (str): Тикер компании.

        Выходные данные:
            Optional[float]: Текущая цена актива.
            Возвращает None, если тикер не найден или API недоступно.
        """
        companies = self.get_companies()
        if companies and "companies" in companies:
            if ticker in companies["companies"]:
                return companies["companies"][ticker].get("price")
        return None
    
    def get_portfolio_value(self) -> Optional[float]:
        """
        Получает текущую оценку всего портфеля (Эквити).

        Выходные данные:
            Optional[float]: Текущая стоимость портфеля.
            Возвращает None при ошибке запроса.
        """
        account = self.get_account_info()
        if account:
            return account["balances"].get("portfolio_value_current")
        return None
    
    def get_cash_balance(self) -> Optional[float]:
        """
        Получает свободный остаток денежных средств на счете.

        Выходные данные:
            Optional[float]: Баланс свободных средств (cash).
            Возвращает None при ошибке запроса.
        """
        account = self.get_account_info()
        if account:
            return account["balances"].get("cash")
        return None
    
    def get_uds(self) -> Optional[float]:
        """
        Получает показатель Уровня Достаточности Средств (УДС) пользователя.

        Выходные данные:
            Optional[float]: Текущий УДС.
            Возвращает None при ошибке запроса.
        """
        account = self.get_account_info()
        if account:
            return account.get("uds")
        return None
    
    def is_healthy(self) -> bool:
        """
        Проверяет, находится ли счет в безопасности от маржин-колла.

        Выходные данные:
            bool: True, если УДС > 0 (счет в норме), иначе False.
        """
        uds = self.get_uds()
        return uds is not None and uds > 0