"""
Класс MarketEngine: орган рынка, управляет всеми компаниями.
Рассчитывает цены, выплачивает дивиденды, обрабатывает события.
"""

import numpy as np
from typing import Dict, List, Any, Optional
from src.market_engine.company import Company
from src.utils.market_math import PriceCalculator


class NewsEvent:
    """Временное событие, которое влияет на компании или сектора."""
    
    def __init__(self, 
                 event_id: str,
                 name: str,
                 target_type: str,  # "company", "sector", "market"
                 target_value: str,  # ticker, sector name, или "MARKET"
                 impact_profit: float = 0.0,  # Влияние на прибыль
                 impact_volatility: float = 1.0,  # Множитель волатильности
                 duration_ticks: int = 10,
                 decay_type: str = "linear"):  # "linear" или "shock"
        """
        Args:
            event_id: Уникальный идентификатор
            name: Название события
            target_type: "company", "sector", "market"
            target_value: Значение цели (ticker, имя сектора, "MARKET")
            impact_profit: Влияние на прибыль (абсолютное значение)
            impact_volatility: Множитель волатильности
            duration_ticks: Как долго действует событие
            decay_type: Как спадает эффект ("linear" или "shock")
        """
        self.event_id = event_id
        self.name = name
        self.target_type = target_type
        self.target_value = target_value
        self.impact_profit = impact_profit
        self.impact_volatility = impact_volatility
        self.duration_ticks = duration_ticks
        self.remaining_ticks = duration_ticks
        self.decay_type = decay_type
    
    def get_current_impact(self) -> float:
        """Возвращает текущую интенсивность события (0.0 - 1.0)."""
        if self.remaining_ticks <= 0:
            return 0.0
        
        if self.decay_type == "linear":
            return self.remaining_ticks / self.duration_ticks
        elif self.decay_type == "shock":
            if self.remaining_ticks > self.duration_ticks * 0.75:
                return 1.0
            else:
                return 0.0
        return 1.0
    
    def tick(self) -> bool:
        """Уменьшает время жизни события. Возвращает True, если событие ещё актуально."""
        self.remaining_ticks -= 1
        return self.remaining_ticks > 0


class MarketEngine:
    """Основной движок рынка: управляет компаниями, ценами, дивидендами, событиями."""
    
    def __init__(self, seed: int = None):
        """
        Args:
            seed: Seed для RNG (для воспроизводимости)
        """
        self.companies: Dict[str, Company] = {}
        self.events: List[NewsEvent] = []
        self.index_price: float = 100.0
        self.index_history: List[float] = []
        self.price_calc = PriceCalculator(seed)
        self.tick_count: int = 0
    
    def add_company(self, company: Company) -> None:
        """Добавляет компанию в рынок."""
        self.companies[company.ticker] = company
        if not company.price_history:
            company.price_history = [company.price]
    
    def get_company(self, ticker: str) -> Optional[Company]:
        return self.companies.get(ticker)
    
    def add_event(self, event: NewsEvent) -> None:
        self.events.append(event)
    
    def update_all_prices(self) -> None:
        """
        Обновляет цены всех компаний.
        Это главный метод, вызывается один раз за тик.
        
        Для каждой компании:
        1. Обновляем прибыль (+ случайный шум)
        2. Рассчитываем новую цену (броуновское движение + фундаментальный тренд)
        3. Сохраняем в историю
        """
        for ticker, company in self.companies.items():
            if company.is_index:
                continue
            
            profit_noise = np.random.uniform(-1, 1)
            company.update_profit(profit_noise)
            
            new_price = self.price_calc.calculate_next_price(
                current_price=company.price,
                current_profit=company.profit_current,
                base_profit=company.profit_base,
                volatility=company.volatility,
            )
            company.price = new_price
            company.add_price_history()
        
        self.update_index()
    
    def check_dividends(self) -> Dict[str, float]:
        """
        Проверяет, пора ли выплачивать дивиденды.
        Возвращает словарь выплаченных дивидендов {ticker: amount}.
        
        Вызывается в начале каждого тика.
        """
        dividends = {}
        
        for ticker, company in self.companies.items():
            if company.is_index:
                continue
            if company.decrement_dividend_counter():
                div_amount = company.apply_dividend()
                dividends[ticker] = div_amount
        
        return dividends
    
    def update_events(self) -> None:
        """
        Обновляет эффекты событий.
        Каждый тик: уменьшаем время жизни события, удаляем мёртвые события.
        """
        active_events = []
        for event in self.events:
            if event.tick():
                active_events.append(event)
        
        self.events = active_events
    
    def apply_events_to_companies(self) -> None:
        """
        Применяет текущие эффекты всех событий к компаниям.
        Вызывается после update_events().
        """
        for event in self.events:
            impact_strength = event.get_current_impact()
            
            if event.target_type == "company":
                company = self.companies.get(event.target_value)
                if company:
                    company.apply_event_impact(
                        impact_on_profit=event.impact_profit * impact_strength,
                        impact_on_volatility=1 + (event.impact_volatility - 1) * impact_strength
                    )
            
            elif event.target_type == "sector":
                sector_name = event.target_value
                for company in self.companies.values():
                    if not company.is_index and sector_name in company.sectors:
                        company.apply_event_impact(
                            impact_on_profit=event.impact_profit * impact_strength * 0.5,  # Слабее
                            impact_on_volatility=1 + (event.impact_volatility - 1) * impact_strength * 0.7
                        )
            
            elif event.target_type == "market":
                for company in self.companies.values():
                    if not company.is_index:
                        company.apply_event_impact(
                            impact_on_profit=event.impact_profit * impact_strength * 0.1,
                            impact_on_volatility=1 + (event.impact_volatility - 1) * impact_strength * 0.2
                        )
    
    def update_index(self) -> None:
        """
        Пересчитывает индекс биржи как простую среднюю цену всех компаний.
        """
        non_index_companies = [
            c for c in self.companies.values() if not c.is_index
        ]
        if not non_index_companies:
            return
        avg_price = sum(c.price for c in non_index_companies) / len(non_index_companies)
        self.index_price = avg_price
        self.index_history.append(self.index_price)
        if len(self.index_history) > 1000:
            self.index_history = self.index_history[-1000:]
    
    def tick(self) -> None:
        """
        Основной цикл одного тика.
        Вызывается один раз за виртуальный час (реально за ~0.5 секунд).
        
        Последовательность:
        1. Выплачиваем дивиденды (в начале тика)
        2. Обновляем все цены
        3. Обновляем эффекты событий
        4. Применяем события к компаниям
        """
        self.tick_count += 1
        dividends = self.check_dividends()
        self.update_all_prices()
        self.update_events()
        self.apply_events_to_companies()
    
    def get_market_snapshot(self) -> Dict[str, Any]:
        """
        Возвращает текущее состояние рынка для API.
        """
        return {
            "tick_count": self.tick_count,
            "index_price": self.index_price,
            "companies": {
                ticker: {
                    "ticker": c.ticker,
                    "name": c.name,
                    "description": c.description,
                    "sectors": c.sectors,
                    "price": c.price,
                    "price_change": c.price_history[-2:] if len(c.price_history) >= 2 else [c.price],
                    "volatility": c.volatility,
                }
                for ticker, c in self.companies.items()
                if not c.is_index
            }
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализует движок в словарь (для JSON)."""
        return {
            "tick_count": self.tick_count,
            "index_price": self.index_price,
            "index_history": self.index_history[-168:],
            "companies": {
                ticker: company.to_dict()
                for ticker, company in self.companies.items()
            },
            "events": [
                {
                    "event_id": e.event_id,
                    "name": e.name,
                    "target_type": e.target_type,
                    "target_value": e.target_value,
                    "remaining_ticks": e.remaining_ticks,
                }
                for e in self.events
            ]
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'MarketEngine':
        """Десериализует движок из словаря (из JSON)."""
        engine = MarketEngine()
        engine.tick_count = data.get("tick_count", 0)
        engine.index_price = data.get("index_price", 100.0)
        engine.index_history = data.get("index_history", [])
        
        for ticker, company_data in data.get("companies", {}).items():
            company = Company.from_dict(company_data)
            engine.add_company(company)
        
        return engine