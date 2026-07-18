"""
Класс Company: представляет одну компанию (актив) на бирже.
Хранит все данные о котировке, прибыли, дивидендах и историю цен.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any
from datetime import datetime


@dataclass
class Company:
    """Представление одной компании на бирже."""
    
    # ===== ИДЕНТИФИКАЦИЯ =====
    ticker: str                      # "GIGA", "PWR", и т.д.
    name: str                        # "GigaTech"
    description: str                 # "AI и облачные вычисления"
    sectors: List[str] = field(default_factory=list)  # ["Tech", "AI"]
    
    # ===== РЫНОК =====
    price: float = 100.0             # Текущая цена
    volatility: float = 0.15         # Коэффициент волатильности (15% за тик)
    price_history: List[float] = field(default_factory=list)
    
    # ===== ФУНДАМЕНТАЛ =====
    profit_base: float = 500000.0    # Базовая прибыль (якорь)
    profit_current: float = 500000.0 # Текущая прибыль (растёт каждый тик)
    profit_growth: float = 1000.0    # Шаг роста прибыли за тик
    profit_last_dividend: float = 500000.0  # Прибыль в момент последней выплаты
    
    # ===== ДИВИДЕНДЫ =====
    div_payout_ratio: float = 0.5    # 50% от прибыли идёт на выплату
    div_period_ticks: int = 168      # Выплата каждые 168 тиков (неделя)
    ticks_to_next_dividend: int = 168  # Сколько тиков до следующей выплаты
    
    # ===== СЛУЖЕБНЫЕ =====
    is_index: bool = False           # Является ли это индексом (не торгуется)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def __post_init__(self):
        """Инициализация после создания dataclass."""
        if not self.price_history:
            self.price_history = [self.price]
        if self.profit_current == 0:
            self.profit_current = self.profit_base
    
    def update_profit(self, noise_factor: float = 0.0) -> None:
        """
        Обновляет текущую прибыль на один тик.
        Прибыль растет линейно на profit_growth + шум.
        
        Args:
            noise_factor: Случайный шум от -1 до +1 (множится на profit_growth)
        """
        self.profit_current += self.profit_growth
        self.profit_current += self.profit_growth * noise_factor * 0.5
        if self.profit_current < 0:
            self.profit_current = 0
    
    def calc_dividend_amount(self) -> float:
        """
        Рассчитывает размер дивиденда на одну акцию.
        
        Формула: (current_profit * payout_ratio) / 1000000
        (предполагаем 1M акций в обращении)
        
        Returns:
            Размер дивиденда на одну акцию
        """
        if self.profit_current <= 0:
            return 0.0
        
        total_payout = self.profit_current * self.div_payout_ratio
        shares_outstanding = 1_000_000
        dividend_per_share = total_payout / shares_outstanding
        
        return max(dividend_per_share, 0)
    
    def apply_dividend(self) -> float:
        """
        Применяет дивиденд: обваливает цену и обновляет счётчик.
        Это должно вызваться в начале тика, если пришла пора выплачивать.
        
        Returns:
            Размер дивиденда (для логирования)
        """
        dividend = self.calc_dividend_amount()
        if dividend > 0:
            self.price = max(self.price - dividend, 0.01)
            self.profit_last_dividend = self.profit_current
            self.ticks_to_next_dividend = self.div_period_ticks
        return dividend
    
    def add_price_history(self) -> None:
        """Добавляет текущую цену в историю (вызывается каждый тик)."""
        self.price_history.append(self.price)
        
        if len(self.price_history) > 1000:
            self.price_history = self.price_history[-1000:]
    
    def apply_event_impact(self, impact_on_profit: float = 0.0, 
                          impact_on_volatility: float = 0.0) -> None:
        """
        Применяет влияние новости на компанию.
        
        Args:
            impact_on_profit: Абсолютное изменение profit_base 
                             (напр. -50000 = "завод сгорел")
            impact_on_volatility: Множитель волатильности 
                                 (напр. 2.0 = волатильность удвоилась)
        """
        if impact_on_profit != 0:
            self.profit_base = max(self.profit_base + impact_on_profit, 0)
            self.profit_current = max(self.profit_current + impact_on_profit, 0)
        
        if impact_on_volatility > 0:
            self.volatility = min(self.volatility * impact_on_volatility, 1.0)
    
    def decrement_dividend_counter(self) -> bool:
        """
        Уменьшает счётчик дивидендов на 1.
        Возвращает True, если пора выплачивать дивиденд.
        """
        self.ticks_to_next_dividend -= 1
        return self.ticks_to_next_dividend <= 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализует компанию в словарь (для JSON)."""
        return {
            "ticker": self.ticker,
            "name": self.name,
            "description": self.description,
            "sectors": self.sectors,
            "price": self.price,
            "volatility": self.volatility,
            "price_history": self.price_history[-168:],  # Последние 168 тиков (неделя)
            "profit_base": self.profit_base,
            "profit_current": self.profit_current,
            "profit_growth": self.profit_growth,
            "profit_last_dividend": self.profit_last_dividend,
            "div_payout_ratio": self.div_payout_ratio,
            "div_period_ticks": self.div_period_ticks,
            "ticks_to_next_dividend": self.ticks_to_next_dividend,
            "is_index": self.is_index,
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Company':
        """Десериализует компанию из словаря (из JSON)."""
        company = Company(
            ticker=data["ticker"],
            name=data["name"],
            description=data.get("description", ""),
            sectors=data.get("sectors", []),
            price=data.get("price", 100.0),
            volatility=data.get("volatility", 0.15),
            price_history=data.get("price_history", []),
            profit_base=data.get("profit_base", 500000.0),
            profit_current=data.get("profit_current", 500000.0),
            profit_growth=data.get("profit_growth", 1000.0),
            profit_last_dividend=data.get("profit_last_dividend", 500000.0),
            div_payout_ratio=data.get("div_payout_ratio", 0.5),
            div_period_ticks=data.get("div_period_ticks", 168),
            ticks_to_next_dividend=data.get("ticks_to_next_dividend", 168),
            is_index=data.get("is_index", False),
        )
        return company