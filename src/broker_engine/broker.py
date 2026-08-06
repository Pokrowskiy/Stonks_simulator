"""
Класс Broker: управляет счётами пользователей, обрабатывает ордера.
Рассчитывает маржу, проверяет УДС, проводит ликвидации.
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from src.broker_engine.broker_account import BrokerAccount


class OrderExecutionError(Exception):
    """Ошибка при исполнении ордера."""
    pass


class Order:
    """Представление одного ордера (заявки на покупку/продажу)."""
    
    def __init__(self, 
                 username: str,
                 ticker: str,
                 action: str,  # "BUY" или "SELL"
                 quantity: int,
                 price: float,
                 order_id: str = None):
        """
        Args:
            username: Кто выполняет ордер
            ticker: На какой актив
            action: "BUY" или "SELL"
            quantity: Количество акций
            price: По какой цене
            order_id: Уникальный ID (автогенерируется если не задан)
        """
        self.username = username
        self.ticker = ticker
        self.action = action.upper()
        self.quantity = quantity
        self.price = price
        self.order_id = order_id or f"{username}_{ticker}_{datetime.now().timestamp()}"
        self.timestamp = datetime.now().isoformat()
        self.status = "PENDING"  # PENDING, EXECUTED, REJECTED
        self.rejection_reason = None
        self.executed_price = None
        self.commission = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализует ордер в словарь."""
        return {
            "order_id": self.order_id,
            "username": self.username,
            "ticker": self.ticker,
            "action": self.action,
            "quantity": self.quantity,
            "price": self.price,
            "timestamp": self.timestamp,
            "status": self.status,
            "rejection_reason": self.rejection_reason,
            "executed_price": self.executed_price,
            "commission": self.commission,
        }


class Broker:
    """Основной брокер: управляет счётами и ордерами."""
    
    def __init__(self):
        """Инициализация Брокера."""
        self.accounts: Dict[str, BrokerAccount] = {}
        self.order_history: List[Order] = []
        self.commission_leverage_daily = 0.0001  # 0.01% от объёма плеча в день
        self.commission_trade = 0.001  # 0.1% при открытии/закрытии сделки
        self.liquidation_discount = 0.95  # 5% скидка при ликвидации
        self.tick_count = 0
    
    # ===== УПРАВЛЕНИЕ СЧЁТАМИ =====
    
    def create_account(self, username: str, initial_balance: float) -> BrokerAccount:
        """
        Создаёт новый счёт.
        
        Args:
            username: Имя пользователя
            initial_balance: Начальный баланс
            
        Returns:
            BrokerAccount
            
        Raises:
            ValueError: Если счёт уже существует
        """
        if username in self.accounts:
            raise ValueError(f"Счёт {username} уже существует")
        
        account = BrokerAccount(
            username=username,
            cash_balance=initial_balance,
            start_value=initial_balance,
            day_start_value=initial_balance,
            week_start_value=initial_balance,
        )
        
        self.accounts[username] = account
        return account
    
    def get_account(self, username: str) -> Optional[BrokerAccount]:
        """Получает счёт по имени пользователя."""
        return self.accounts.get(username)
    
    def account_exists(self, username: str) -> bool:
        """Проверяет, существует ли счёт."""
        return username in self.accounts
    
    # ===== ОБРАБОТКА ОРДЕРОВ =====
    
    def execute_order(self, 
                     username: str,
                     ticker: str,
                     action: str,
                     quantity: int,
                     current_price: float,
                     volatilities: Dict[str, float]) -> Order:
        """
        Выполняет ордер (покупка/продажа актива).
        
        Алгоритм:
        1. Проверяем, существует ли счёт
        2. Симулируем изменение позиции
        3. Рассчитываем гипотетический УДС
        4. Если УДС > 1: одобряем, иначе отклоняем
        
        Args:
            username: Кто выполняет
            ticker: На какой актив
            action: "BUY" или "SELL"
            quantity: Количество акций
            current_price: Текущая цена (от Market Engine)
            volatilities: Словарь волатильностей {ticker: volatility}
            
        Returns:
            Order (с status = "EXECUTED" или "REJECTED")
            
        Raises:
            OrderExecutionError: Если счёт не найден
        """
        order = Order(username, ticker, action, quantity, current_price)
        
        # Проверяем счёт
        account = self.get_account(username)
        if not account:
            order.status = "REJECTED"
            order.rejection_reason = f"Счёт {username} не найден"
            self.order_history.append(order)
            raise OrderExecutionError(order.rejection_reason)
        
        if account.is_liquidated:
            order.status = "REJECTED"
            order.rejection_reason = "Счёт ликвидирован"
            self.order_history.append(order)
            raise OrderExecutionError(order.rejection_reason)
        
        # Получаем текущие цены для всех позиций
        prices = self._get_all_prices(current_price, ticker)
        
        # Рассчитываем комиссию
        order_commission = abs(quantity) * current_price * self.commission_trade
        
        # Симулируем сделку
        # Для BUY: position +, cash -
        # Для SELL: position -, cash +
        
        if action.upper() == "BUY":
            # Денежные средства = cash - (quantity × price) - commission
            cash_after = account.cash_balance - (quantity * current_price + order_commission)
        elif action.upper() == "SELL":
            # Денежные средства = cash + (quantity × price) - commission
            cash_after = account.cash_balance + (quantity * current_price - order_commission)
        else:
            order.status = "REJECTED"
            order.rejection_reason = "Неизвестное действие (BUY или SELL)"
            self.order_history.append(order)
            raise OrderExecutionError(order.rejection_reason)
        
        # Симулируем новую позицию
        old_position = account.positions.get(ticker, 0)
        if action.upper() == "BUY":
            new_position = old_position + quantity
        else:
            new_position = old_position - quantity
        
        # Проверяем гипотетический УДС
        # Создаём временное состояние
        test_positions = account.positions.copy()
        if new_position == 0:
            test_positions.pop(ticker, None)
        else:
            test_positions[ticker] = new_position
        
        test_portfolio_value = cash_after + sum(
            test_positions.get(t, 0) * prices.get(t, 0)
            for t in test_positions
        )
        
        # Рассчитываем гипотетическую маржу
        test_initial_margin = 0.0
        for t, qty in test_positions.items():
            if t in prices:
                position_value = abs(qty) * prices[t]
                risk_rate = account.calc_risk_rate(t, volatilities.get(t, 0.15))
                test_initial_margin += position_value * risk_rate
        
        test_min_margin = test_initial_margin / 2.0
        
        # Рассчитываем гипотетический УДС
        if test_initial_margin == test_min_margin:
            # Нет позиций
            if test_portfolio_value >= test_initial_margin:
                test_uds = 9.99
            else:
                test_uds = -9.99
        else:
            test_uds = (test_portfolio_value - test_min_margin) / (test_initial_margin - test_min_margin)
            test_uds = max(min(test_uds, 9.99), -9.99)
        
        # Если УДС ≤ 1: отклоняем
        if test_uds <= 1.0:
            order.status = "REJECTED"
            order.rejection_reason = f"Недостаточно обеспечения. UДС={test_uds:.2f} (требуется >1.0)"
            self.order_history.append(order)
            return order
        
        # ОДОБРЯЕМ ОРДЕР
        order.status = "EXECUTED"
        order.executed_price = current_price
        order.commission = order_commission
        
        # Обновляем счёт
        account.cash_balance = cash_after
        
        # Обновляем позицию (с отслеживанием средней цены входа)
        quantity_change = quantity if action == "BUY" else -quantity
        account.add_position(ticker, quantity_change, current_price)
        
        self.order_history.append(order)
        
        return order
    
    def _get_all_prices(self, current_price: float, ticker: str) -> Dict[str, float]:
        """
        Вспомогательный метод для получения цен всех позиций.
        В реальности должен получать от Market Engine.
        Для MVP: возвращает current_price для нужного тикера.
        
        Args:
            current_price: Цена текущего тикера
            ticker: Тикер, по которому ордер
            
        Returns:
            Словарь {ticker: price}
        """
        prices = {}
        
        # Для всех позиций у всех пользователей добавляем какую-то цену
        for account in self.accounts.values():
            for t in account.positions.keys():
                if t not in prices:
                    if t == ticker:
                        prices[t] = current_price
                    else:
                        # В реальности нужно получить от Market Engine
                        # Для теста: допустим, цена стабильная
                        prices[t] = 100.0  # плейсхолдер
        
        prices[ticker] = current_price
        
        return prices
    
    # ===== ПРОВЕРКА МАРЖИ И ЛИКВИДАЦИЯ =====
    
    def check_liquidations(self, 
                          prices: Dict[str, float],
                          volatilities: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
        """
        Проверяет УДС для всех счётов и ликвидирует, если нужно.
        
        Args:
            prices: Словарь {ticker: price} от Market Engine
            volatilities: Словарь {ticker: volatility} от Market Engine
            
        Returns:
            Словарь {username: результат_ликвидации} (только для ликвидированных)
        """
        liquidations = {}
        
        for username, account in self.accounts.items():
            if account.is_liquidated:
                continue  # Уже ликвидирован
            
            # Рассчитываем УДС
            uds = account.calc_uds(prices, volatilities)
            
            # Если УДС ≤ 0: ликвидируем
            if uds <= 0.0:
                proceeds = account.liquidate_all_positions(
                    prices,
                    self.liquidation_discount
                )
                
                liquidations[username] = {
                    "timestamp": datetime.now().isoformat(),
                    "uds": uds,
                    "liquidation_proceeds": proceeds,
                    "final_cash_balance": account.cash_balance,
                    "info": account.liquidation_info
                }
        
        return liquidations
    
    # ===== ДНЕВНЫЕ/НЕДЕЛЬНЫЕ ОПЕРАЦИИ =====
    
    def apply_dividends(self, dividends: Dict[str, float]) -> None:
        """
        Применяет дивиденды от компаний к счётам пользователей.
        
        Вызывается один раз в день (в конце тика, когда дивиденды выплачены).
        
        Args:
            dividends: Словарь {ticker: dividend_per_share}
                      (returns from market_engine.check_dividends())
        """
        if not dividends:
            return
        
        for account in self.accounts.values():
            for ticker, dividend_per_share in dividends.items():
                # Проверяем, есть ли позиция в этом тикере
                quantity = account.positions.get(ticker, 0)
                if quantity > 0:  # Только LONG позиции получают дивиденды
                    dividend_income = quantity * dividend_per_share
                    account.cash_balance += dividend_income
                    # print(f"✓ {account.username}: +${dividend_income:.2f} дивиденды {ticker}")
    
    def on_daily_tick(self, 
                     prices: Dict[str, float],
                     volatilities: Dict[str, float]) -> None:
        """
        Вызывается в конец каждого дня (tick % 24 == 0).
        
        Что происходит:
        1. Рассчитываем комиссию на плечо и вычитаем из баланса
        2. Фиксируем текущую стоимость портфеля в историю
        
        Args:
            prices: Текущие цены
            volatilities: Волатильности
        """
        for account in self.accounts.values():
            # 1. Вычитаем комиссию за плечо
            leverage_value = 0.0
            for ticker, quantity in account.positions.items():
                if ticker in prices and quantity < 0:  # Шорт = плечо
                    leverage_value += abs(quantity) * prices[ticker]
            
            daily_leverage_commission = leverage_value * self.commission_leverage_daily
            account.cash_balance -= daily_leverage_commission
            
            portfolio_value = account.calc_portfolio_value(prices)
            account.record_daily_snapshot(portfolio_value)
    
    def on_weekly_tick(self,
                      prices: Dict[str, float]) -> None:
        for account in self.accounts.values():
            portfolio_value = account.calc_portfolio_value(prices)
            account.record_weekly_snapshot(portfolio_value)
    
    # ===== ИНФОРМАЦИЯ И СТАТИСТИКА =====
    
    def get_account_summary(self, username: str, prices: dict, volatilities: dict) -> dict:
        """Получить сводку по счёту."""
        account = self.get_account(username)
    
        if not account:
            raise ValueError(f"Account {username} not found")
        
        portfolio_value = account.calc_portfolio_value(prices)
        initial_margin = account.calc_initial_margin(prices, volatilities)
        min_margin = account.calc_min_margin(prices, volatilities)
        uds = account.calc_uds(prices, volatilities)
        uds_status = account.get_uds_status(uds)
        
        return {
            "username": account.username,
            "uds": uds,
            "uds_status": uds_status,
            "balances": {
                "cash": account.cash_balance,
                "portfolio_value_current": portfolio_value,
                "portfolio_value_start": account.start_value
            },
            "margins": {
                "initial_margin": initial_margin,
                "min_margin": min_margin
            },
            "pnl": {
                "daily_pnl": account.get_daily_pnl(portfolio_value),
                "daily_pnl_percent": account.get_daily_pnl_percent(portfolio_value),
                "weekly_pnl": account.get_weekly_pnl(portfolio_value),
                "total_pnl": account.get_total_pnl(portfolio_value),
                "total_return_percent": account.get_total_return_percent(portfolio_value),
            },
            "positions": [
                {
                    "ticker": ticker,
                    "quantity": quantity,
                    "entry_price": account.entry_prices.get(ticker, 0.0),
                    "current_price": prices.get(ticker, 0),
                    "position_value": quantity * prices.get(ticker, 0),
                    "pnl_daily": (prices.get(ticker, 0) - account.entry_prices.get(ticker, 0)) * quantity,
                    "pnl_total": (prices.get(ticker, 0) - account.entry_prices.get(ticker, 0)) * quantity
                }
                for ticker, quantity in account.positions.items()
            ],
            "is_liquidated": account.is_liquidated
        }

    def get_all_accounts_summary(self, prices: dict, volatilities: dict) -> list:
        """Получить сводку по всем счётам."""
        summaries = []
        for username in self.accounts.keys():
            try:
                summary = self.get_account_summary(username, prices, volatilities)
                summaries.append(summary)
            except:
                pass
        return summaries
    
    def get_order_history(self, username: str = None, limit: int = 50) -> List[Order]:
        """
        Получает историю ордеров.
        
        Args:
            username: Если указан, только ордеры этого пользователя
            limit: Максимум последних ордеров
            
        Returns:
            Список ордеров
        """
        orders = self.order_history
        
        if username:
            orders = [o for o in orders if o.username == username]
        
        return orders[-limit:]
    
    # ===== СЕРИАЛИЗАЦИЯ =====
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализует состояние Брокера в словарь (для JSON)."""
        return {
            "accounts": {
                username: account.to_dict()
                for username, account in self.accounts.items()
            },
            "order_history": [o.to_dict() for o in self.order_history[-1000:]],  # Последние 1000
            "commission_leverage_daily": self.commission_leverage_daily,
            "commission_trade": self.commission_trade,
            "liquidation_discount": self.liquidation_discount,
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Broker':
        """Десериализует Брокера из словаря (из JSON)."""
        broker = Broker()
        broker.commission_leverage_daily = data.get("commission_leverage_daily", 0.0001)
        broker.commission_trade = data.get("commission_trade", 0.001)
        broker.liquidation_discount = data.get("liquidation_discount", 0.95)
        
        for username, account_data in data.get("accounts", {}).items():
            account = BrokerAccount.from_dict(account_data)
            broker.accounts[username] = account
        return broker