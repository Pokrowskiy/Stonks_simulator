"""
Класс BrokerAccount: представляет счёт одного инвестора.
Хранит позиции, баланс, историю портфеля, расчитывает маржу и УДС.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime


@dataclass
class BrokerAccount:
    """Инвестиционный счёт у брокера."""
    
    # ===== ИДЕНТИФИКАЦИЯ =====
    username: str                           # Уникальное имя пользователя
    
    # ===== АКТИВЫ =====
    cash_balance: float = 0.0               # Свободные деньги (может быть < 0 при плече)
    positions: Dict[str, int] = field(default_factory=dict)  # {"GIGA": 50, "PWR": -10}
    entry_prices: Dict[str, float] = field(default_factory=dict)  # {"GIGA": 150.0, "PWR": 45.5}
    
    # ===== АНАЛИТИКА =====
    start_value: float = 0.0                # Стоимость портфеля при создании
    day_start_value: float = 0.0            # Стоимость в начало текущего дня
    week_start_value: float = 0.0           # Стоимость в начало текущей недели
    portfolio_history: List[float] = field(default_factory=list)  # История PV
    
    # ===== СЛУЖЕБНЫЕ =====
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    is_liquidated: bool = False             # Счёт ликвидирован?
    liquidation_info: Optional[Dict[str, Any]] = None  # Инфо о ликвидации
    
    def __post_init__(self):
        """Инициализация после создания."""
        if not self.start_value:
            self.start_value = self.cash_balance
        if not self.day_start_value:
            self.day_start_value = self.cash_balance
        if not self.week_start_value:
            self.week_start_value = self.cash_balance
        
        # Инициализируем entry_prices для существующих позиций
        for ticker in self.positions:
            if ticker not in self.entry_prices:
                self.entry_prices[ticker] = 0.0
    
    # ===== ОСНОВНЫЕ РАСЧЁТЫ =====
    
    def calc_portfolio_value(self, prices: Dict[str, float]) -> float:
        """
        Рассчитывает текущую стоимость портфеля (эквити).
        
        Формула: PV = cash_balance + Σ(position_size × price)
        
        Args:
            prices: Словарь {ticker: price}
            
        Returns:
            Стоимость портфеля в деньгах
        """
        portfolio_value = self.cash_balance
        
        for ticker, quantity in self.positions.items():
            if ticker in prices:
                portfolio_value += quantity * prices[ticker]
        
        return portfolio_value
    
    def calc_risk_rate(self, ticker: str, volatility: float) -> float:
        """
        Рассчитывает ставку риска для актива на основе волатильности.
        
        Более волатильные активы требуют больше маржи.
        
        Formula: risk_rate = 0.25 + volatility × 0.5
        
        Args:
            ticker: Тикер актива
            volatility: Коэффициент волатильности (напр. 0.15)
            
        Returns:
            Ставка риска (напр. 0.325 = нужно 32.5% маржи)
        """
        risk_rate = 0.25 + volatility * 0.5
        
        risk_rate = min(risk_rate, 0.50)
        
        return risk_rate
    
    def calc_initial_margin(self, prices: Dict[str, float], 
                           volatilities: Dict[str, float]) -> float:
        """
        Рассчитывает начальную маржу (требуемое обеспечение).
        
        Формула: Initial_Margin = Σ(|position_size| × price × risk_rate)
        
        Args:
            prices: Словарь {ticker: price}
            volatilities: Словарь {ticker: volatility}
            
        Returns:
            Сумма маржи в деньгах
        """
        margin = 0.0
        
        for ticker, quantity in self.positions.items():
            if ticker not in prices:
                continue
            
            position_value = abs(quantity) * prices[ticker]
            risk_rate = self.calc_risk_rate(
                ticker,
                volatilities.get(ticker, 0.15)
            )
            margin += position_value * risk_rate
        
        return margin
    
    def calc_min_margin(self, prices: Dict[str, float],
                       volatilities: Dict[str, float]) -> float:
        """
        Рассчитывает минимальную маржу (уровень ликвидации).
        
        Формула: Min_Margin = Initial_Margin / 2
        
        Args:
            prices: Словарь {ticker: price}
            volatilities: Словарь {ticker: volatility}
            
        Returns:
            Минимальная маржа
        """
        initial_margin = self.calc_initial_margin(prices, volatilities)
        return initial_margin / 2.0
    
    def calc_uds(self, prices: Dict[str, float],
                 volatilities: Dict[str, float]) -> float:
        """
        Рассчитывает Уровень Достаточности Средств (УДС).
        
        Формула: УДС = (Portfolio_Value - Min_Margin) / (Initial_Margin - Min_Margin)
        
        Результат clipped в диапазон [-9.99, +9.99].
        
        Args:
            prices: Словарь {ticker: price}
            volatilities: Словарь {ticker: volatility}
            
        Returns:
            УДС (float, от -9.99 до +9.99)
        """
        portfolio_value = self.calc_portfolio_value(prices)
        initial_margin = self.calc_initial_margin(prices, volatilities)
        min_margin = self.calc_min_margin(prices, volatilities)
        
        if initial_margin == min_margin:
            # Нет позиций или маржа не требуется
            if portfolio_value >= initial_margin:
                return 9.99  # Зелёная зона
            else:
                return -9.99  # Красная зона
        
        uds = (portfolio_value - min_margin) / (initial_margin - min_margin)
        
        uds = max(uds, -9.99)
        uds = min(uds, 9.99)
        
        return uds
    
    def get_uds_status(self, uds: float) -> str:
        """
        Возвращает строковый статус УДС.
        
        Args:
            uds: Значение УДС
            
        Returns:
            "NORMAL" / "WARNING" / "LIQUIDATION"
        """
        if uds > 1.0:
            return "NORMAL"
        elif uds > 0.0:
            return "WARNING"
        else:
            return "LIQUIDATION"
    
    # ===== МАНИПУЛЯЦИЯ ПОЗИЦИЯМИ =====
    
    def add_position(self, ticker: str, quantity: int, price: float = 0.0) -> None:
        """
        Добавляет позицию (или увеличивает существующую).
        Обновляет среднюю цену входа при покупке.
        
        Args:
            ticker: Тикер актива
            quantity: Количество акций (может быть отрицательным для шорта)
            price: Цена покупки/продажи
        """
        if ticker not in self.positions:
            self.positions[ticker] = 0
            self.entry_prices[ticker] = 0.0
        
        old_qty = self.positions[ticker]
        new_qty = old_qty + quantity
        
        # Обновляем среднюю цену входа (при увеличении позиции)
        if quantity > 0 and new_qty > 0:
            # Вычисляем новую среднюю цену
            if old_qty > 0:
                # Увеличиваем существующую позицию
                old_avg = self.entry_prices.get(ticker, price)
                self.entry_prices[ticker] = (old_qty * old_avg + quantity * price) / new_qty
            else:
                # Открываем новую позицию или выходим из шорта
                self.entry_prices[ticker] = price
        elif quantity < 0 and new_qty < 0:
            # При шорте - обновляем цену шорта
            if old_qty < 0:
                old_avg = self.entry_prices.get(ticker, price)
                self.entry_prices[ticker] = (abs(old_qty) * old_avg + abs(quantity) * price) / abs(new_qty)
            else:
                self.entry_prices[ticker] = price
        elif new_qty == 0:
            # Позиция закрыта - удаляем
            del self.positions[ticker]
            if ticker in self.entry_prices:
                del self.entry_prices[ticker]
            return
        
        self.positions[ticker] = new_qty
    
    def close_position(self, ticker: str, price: float) -> Dict[str, float]:
        """
        Закрывает позицию полностью и возвращает денежный результат.
        
        Args:
            ticker: Тикер актива
            price: Цена закрытия
            
        Returns:
            Словарь с результатами {"proceeds": деньги, "pnl": прибыль/убыток}
        """
        if ticker not in self.positions or self.positions[ticker] == 0:
            return {"proceeds": 0, "pnl": 0}
        
        quantity = self.positions[ticker]
        
        # Деньги от продажи
        proceeds = quantity * price
        
        # Удаляем позицию
        del self.positions[ticker]
        
        return {
            "proceeds": proceeds,
            "pnl": 0  # PnL считается при закрытии
        }
    
    def liquidate_all_positions(self, prices: Dict[str, float], 
                               liquidation_discount: float = 0.95) -> float:
        """
        Ликвидирует ВСЕ позиции со скидкой (маржин-колл).
        
        Args:
            prices: Словарь {ticker: price}
            liquidation_discount: Скидка при ликвидации (0.95 = на 5% дешевле)
            
        Returns:
            Сумма денег от ликвидации (может быть отрицательной = убыток)
        """
        total_proceeds = 0.0
        liquidated = {}
        
        for ticker, quantity in list(self.positions.items()):
            if ticker not in prices:
                continue
            
            # Цена ликвидации со скидкой
            liquidation_price = prices[ticker] * liquidation_discount
            
            # Деньги
            proceeds = quantity * liquidation_price
            total_proceeds += proceeds
            
            liquidated[ticker] = {
                "quantity": quantity,
                "price": prices[ticker],
                "liquidation_price": liquidation_price,
                "proceeds": proceeds
            }
        
        self.positions.clear()
        
        self.cash_balance += total_proceeds
        
        self.is_liquidated = True
        self.liquidation_info = {
            "timestamp": datetime.now().isoformat(),
            "liquidated_positions": liquidated,
            "total_proceeds": total_proceeds,
            "final_cash_balance": self.cash_balance
        }
        
        return total_proceeds
    
    # ===== ИСТОРИЯ И АНАЛИТИКА =====
    
    def record_daily_snapshot(self, portfolio_value: float) -> None:
        """
        Записывает снимок стоимости портфеля (конец дня).
        
        Args:
            portfolio_value: Текущая стоимость портфеля
        """
        self.portfolio_history.append(portfolio_value)
        self.day_start_value = portfolio_value
        if len(self.portfolio_history) > 2000:
            self.portfolio_history = self.portfolio_history[-2000:]
    
    def record_weekly_snapshot(self, portfolio_value: float) -> None:
        """
        Записывает снимок в начало недели.
        
        Args:
            portfolio_value: Текущая стоимость портфеля
        """
        self.week_start_value = portfolio_value
    
    def get_daily_pnl(self, portfolio_value: float) -> float:
        return portfolio_value - self.day_start_value
    
    def get_daily_pnl_percent(self, portfolio_value: float) -> float:
        if self.day_start_value <= 0:
            return 0.0
        return (self.get_daily_pnl(portfolio_value) / self.day_start_value) * 100
    
    def get_weekly_pnl(self, portfolio_value: float) -> float:
        return portfolio_value - self.week_start_value
    
    def get_total_pnl(self, portfolio_value: float) -> float:
        return portfolio_value - self.start_value
    
    def get_total_return_percent(self, portfolio_value: float) -> float:
        if self.start_value <= 0:
            return 0.0
        return (self.get_total_pnl(portfolio_value) / self.start_value) * 100
    
    # ===== СЕРИАЛИЗАЦИЯ =====
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализует счёт в словарь (для JSON)."""
        return {
            "username": self.username,
            "cash_balance": self.cash_balance,
            "positions": self.positions,
            "entry_prices": self.entry_prices,
            "start_value": self.start_value,
            "day_start_value": self.day_start_value,
            "week_start_value": self.week_start_value,
            "portfolio_history": self.portfolio_history[-168:],  # Последние 168 дней
            "is_liquidated": self.is_liquidated,
            "created_at": self.created_at,
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'BrokerAccount':
        """Десериализует счёт из словаря (из JSON)."""
        account = BrokerAccount(
            username=data["username"],
            cash_balance=data.get("cash_balance", 0.0),
            positions=data.get("positions", {}),
            entry_prices=data.get("entry_prices", {}),
            start_value=data.get("start_value", 0.0),
            day_start_value=data.get("day_start_value", 0.0),
            week_start_value=data.get("week_start_value", 0.0),
            portfolio_history=data.get("portfolio_history", []),
            is_liquidated=data.get("is_liquidated", False),
            created_at=data.get("created_at", datetime.now().isoformat()),
        )
        return account