import numpy as np
from typing import Tuple


class PriceCalculator:
    """Расчёт цены актива на основе фундаментальных показателей и случайности."""
    
    def __init__(self, seed: int = None):
        """
        Args:
            seed: Seed для генератора случайных чисел (для воспроизводимости)
        """
        self.rng = np.random.RandomState(seed)
    
    def brownian_noise(self, volatility: float, mean_reversion_speed: float = 0.05) -> float:
        """
        Генерирует шум на основе броуновского движения с регрессией к среднему.
        
        Args:
            volatility: Коэффициент волатильности (напр. 0.15 = 15% за ТИК, но мы снижаем это)
            mean_reversion_speed: Скорость возврата к среднему (0.0 - 1.0) - УВЕЛИЧЕНА ДО 0.15
            
        Returns:
            Процентное изменение цены (напр. 0.02 = +2%, -0.03 = -3%)
        """
        brownian_step = self.rng.normal(0, volatility / 5)
        
        mean_reversion_pull = -brownian_step * mean_reversion_speed
        
        total_noise = brownian_step + mean_reversion_pull
        
        return total_noise
    
    def profit_to_price_factor(self, current_profit: float, base_profit: float) -> float:
        """
        Конвертирует фундаментальную прибыль в мультипликатор цены.
        Если прибыль выше базовой → цена растёт, ниже → падает.
        
        Использует квадратный корень вместо логарифма для более мягкого влияния.
        
        Args:
            current_profit: Текущая прибыль компании
            base_profit: Базовая/средняя прибыль (якорь)
            
        Returns:
            Мультипликатор цены относительно якоря
        """
        if base_profit <= 0:
            return 1.0
        
        profit_ratio = current_profit / base_profit
        
        price_factor = (profit_ratio)**0.25
        
        return price_factor
    
    def calculate_next_price(
        self,
        current_price: float,
        current_profit: float,
        base_profit: float,
        volatility: float,
        mean_reversion_speed: float = 0.05,
    ) -> float:
        """
        Рассчитывает цену на следующий тик.
        
        Формула:
            price_new = price_old * (
                1 +                                      # Базовая цена
                noise(volatility) +                      # Броуновское движение (снижено)
                (profit_factor - 1) * trend_strength    # Фундаментальный тренд (снижено)
            )
        Args:
            current_price: Текущая цена
            current_profit: Текущая прибыль
            base_profit: Базовая прибыль (для регрессии)
            volatility: Волатильность
            mean_reversion_speed: Скорость возврата к среднему
            
        Returns:
            Новая цена
        """
        noise = self.brownian_noise(volatility, mean_reversion_speed) * 1
        
        profit_factor = self.profit_to_price_factor(current_profit, base_profit) / 2
        
        trend_impact = (profit_factor - 1) * 0.002
        price_change = noise + trend_impact
        price_change = max(min(price_change, 0.05), -0.05)

        new_price = max(current_price * (1 + price_change), 0.01)
        
        return new_price