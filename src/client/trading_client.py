import requests
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

class PermissionError(Exception):
    """Исключение: недостаточно прав для операции."""
    pass

class APIError(Exception):
    """Исключение: ошибка API сервера."""
    pass

@dataclass
class OrderResult:
    """Результат выполнения ордера."""
    order_id: str
    status: str  # "EXECUTED" или "REJECTED"
    rejection_reason: Optional[str] = None
    commission: float = 0.0
    
    def is_executed(self) -> bool:
        return self.status == "EXECUTED"
    
    def __str__(self) -> str:
        if self.is_executed():
            return f"✓ Ордер выполнен (комиссия: ${self.commission:.2f})"
        else:
            return f"✗ Ордер отклонён: {self.rejection_reason}"

@dataclass
class Portfolio:
    """Состояние портфеля пользователя."""
    username: str
    uds: float
    uds_status: str  # "NORMAL", "WARNING", "LIQUIDATION"
    cash: float
    portfolio_value: float
    positions: List[Dict[str, Any]]
    pnl_daily: float
    pnl_daily_percent: float
    pnl_total: float
    pnl_total_percent: float
    is_liquidated: bool
    
    def __str__(self) -> str:
        status_icon = "✓" if self.uds_status == "NORMAL" else "⚠" if self.uds_status == "WARNING" else "✗"
        return (
            f"{status_icon} {self.username}\n"
            f"  УДС: {self.uds:.2f} ({self.uds_status})\n"
            f"  Баланс: ${self.cash:.2f}\n"
            f"  Портфель: ${self.portfolio_value:.2f}\n"
            f"  Дневной PnL: ${self.pnl_daily:.2f} ({self.pnl_daily_percent:.2f}%)\n"
            f"  Общий PnL: ${self.pnl_total:.2f} ({self.pnl_total_percent:.2f}%)\n"
            f"  Позиций: {len(self.positions)}"
        )

class TradingClient:
    """
    Python SDK для Trading Server.
    
    Поддерживает два режима:
    1. Наблюдатель (username=None): только чтение данных
    2. Активный пользователь (username="..."): полный доступ к торговле
    """    
    def __init__(self, base_url: str, username: Optional[str] = None, timeout: int = 10):
        """
        Инициализирует клиент.        
        Args:
            base_url: URL сервера (например, "http://localhost:8000")
            username: Имя пользователя для активной торговли (опционально)
            timeout: Таймаут запросов в секундах
        """
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.timeout = timeout
        self.session = requests.Session()
        
        # Выводим информацию о режиме
        if username:
            print(f"✓ TradingClient инициализирован как {username}")
        else:
            print("✓ TradingClient инициализирован в режиме Наблюдателя")

    def get_market_overview(self) -> Dict[str, Any]:
        """
        Получает обзор рынка: список компаний с ценами и изменениями.
        
        Returns:
            Словарь с информацией о компаниях
        """
        url = f"{self.base_url}/api/market/companies"
        return self._request("GET", url)
    
    def get_company_details(self, ticker: str) -> Dict[str, Any]:
        """
        Получает детальную информацию о компании.
        
        Args:
            ticker: Тикер компании (например, "GIGA")
            
        Returns:
            Словарь с информацией о компании
        """
        url = f"{self.base_url}/api/market/fundamentals/{ticker}"
        return self._request("GET", url)
    
    def get_market_index(self) -> Dict[str, Any]:
        """
        Получает состояние индекса и его историю.
        
        Returns:
            Словарь с информацией об индексе
        """
        url = f"{self.base_url}/api/market/index"
        return self._request("GET", url)
    
    def get_active_events(self) -> Dict[str, Any]:
        """
        Получает список активных событий/новостей на рынке.
        
        Returns:
            Словарь с активными событиями
        """
        url = f"{self.base_url}/api/market/events"
        return self._request("GET", url)
    
    def get_market_status(self) -> Dict[str, Any]:
        """
        Получает общий статус рынка.
        
        Returns:
            Словарь со статусом Market Engine
        """
        url = f"{self.base_url}/api/market/status"
        return self._request("GET", url)
    
    def get_price_history(self, ticker: str, limit: int = 48) -> Dict[str, Any]:
        """
        Получает историю цен компании.
        
        Args:
            ticker: Тикер компании
            limit: Максимальное количество точек истории
            
        Returns:
            Словарь с историей цен
        """
        url = f"{self.base_url}/api/market/history/{ticker}"
        return self._request("GET", url, params={"limit": limit})
    
    def _check_permission(self):
        """Проверяет, имеет ли пользователь права на торговлю."""
        if not self.username:
            raise PermissionError(
                "Операция требует активного пользователя. "
                "Инициализируйте клиент с параметром username="
            )
    
    def get_my_portfolio(self) -> Portfolio:
        """
        Получает полное состояние портфеля пользователя.
        
        Returns:
            Объект Portfolio с информацией о счёте
            
        Raises:
            PermissionError: Если пользователь не авторизован
        """
        self._check_permission()
        
        url = f"{self.base_url}/api/broker/account/{self.username}"
        data = self._request("GET", url)
        
        return Portfolio(
            username=data["username"],
            uds=data["uds"],
            uds_status=data["uds_status"],
            cash=data["balances"]["cash"],
            portfolio_value=data["balances"]["portfolio_value_current"],
            positions=data["positions"],
            pnl_daily=data["pnl"]["daily_pnl"],
            pnl_daily_percent=data["pnl"]["daily_pnl_percent"],
            pnl_total=data["pnl"]["total_pnl"],
            pnl_total_percent=data["pnl"]["total_return_percent"],
            is_liquidated=data["is_liquidated"],
        )
    
    def get_my_orders(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Получает историю ордеров пользователя.
        
        Args:
            limit: Максимальное количество последних ордеров
            
        Returns:
            Список ордеров
            
        Raises:
            PermissionError: Если пользователь не авторизован
        """
        self._check_permission()
        
        url = f"{self.base_url}/api/broker/order-history/{self.username}"
        data = self._request("GET", url, params={"limit": limit})
        return data.get("orders", [])
    
    def buy(self, ticker: str, quantity: int) -> OrderResult:
        """
        Покупает акции.
        
        Args:
            ticker: Тикер компании
            quantity: Количество акций
            
        Returns:
            OrderResult с информацией о выполнении
            
        Raises:
            PermissionError: Если пользователь не авторизован
        """
        self._check_permission()
        return self._place_order(ticker, "BUY", quantity)
    
    def sell(self, ticker: str, quantity: int) -> OrderResult:
        """
        Продаёт акции (закрывает позицию или открывает шорт).
        
        Args:
            ticker: Тикер компании
            quantity: Количество акций
            
        Returns:
            OrderResult с информацией о выполнении
            
        Raises:
            PermissionError: Если пользователь не авторизован
        """
        self._check_permission()
        return self._place_order(ticker, "SELL", quantity)
    
    def _place_order(self, ticker: str, action: str, quantity: int) -> OrderResult:
        """
        Размещает ордер (внутренний метод).
        
        Args:
            ticker: Тикер
            action: "BUY" или "SELL"
            quantity: Количество
            
        Returns:
            OrderResult
        """
        url = f"{self.base_url}/api/broker/order"
        
        payload = {
            "username": self.username,
            "ticker": ticker,
            "action": action,
            "quantity": quantity
        }
        
        data = self._request("POST", url, json=payload)
        
        return OrderResult(
            order_id=data["order_id"],
            status=data["status"],
            rejection_reason=data.get("rejection_reason"),
            commission=data.get("commission", 0.0)
        )
    
    def _request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """
        Выполняет HTTP запрос к серверу.
        
        Args:
            method: HTTP метод ("GET", "POST", "PUT", "DELETE")
            url: Полный URL эндпоинта
            **kwargs: Дополнительные параметры для requests
            
        Returns:
            Распарсенный JSON ответ
            
        Raises:
            APIError: Если сервер вернул ошибку
        """
        try:
            kwargs.setdefault("timeout", self.timeout)
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.HTTPError as e:
            error_msg = f"API ошибка {e.response.status_code}"
            try:
                error_detail = e.response.json().get("detail", "Неизвестная ошибка")
                error_msg += f": {error_detail}"
            except:
                pass
            raise APIError(error_msg)
        
        except requests.exceptions.RequestException as e:
            raise APIError(f"Ошибка подключения: {str(e)}")
        
        except ValueError:
            raise APIError("Ошибка парсинга JSON ответа")
    
    def print_portfolio(self):
        """Выводит портфель в консоль красивым форматом."""
        try:
            portfolio = self.get_my_portfolio()
            print("\n" + "=" * 60)
            print("МОЙ ПОРТФЕЛЬ")
            print("=" * 60)
            print(portfolio)
            print("=" * 60 + "\n")
        except PermissionError as e:
            print(f"✗ {e}")
    
    def print_market_overview(self):
        """Выводит обзор рынка в консоль."""
        try:
            data = self.get_market_overview()
            print("\n" + "=" * 60)
            print("ОБЗОР РЫНКА")
            print("=" * 60)
            
            for company in data.get("companies", []):
                ticker = company["ticker"]
                price = company["price"]
                change = company.get("change_24h", 0)
                change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"
                print(f"  {ticker:10} ${price:8.2f}  {change_str}")
            
            print("=" * 60 + "\n")
        except Exception as e:
            print(f"✗ Ошибка при получении данных: {e}")
    
    def __repr__(self) -> str:
        mode = f"User: {self.username}" if self.username else "Observer"
        return f"<TradingClient {mode} @ {self.base_url}>"