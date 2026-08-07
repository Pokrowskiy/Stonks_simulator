"""
Main Loop Orchestrator: главный цикл симуляции.
"""

import asyncio
from typing import Dict, Any
from src.market_engine.market import MarketEngine
from src.broker_engine.broker import Broker
from src.state_manager.state_manager import StateManager
from src.state_manager.state_manager_config import StateManagerConfig
from src.orchestrator.event_manager import EventManager


class Orchestrator:
    """Оркестратор симуляции: синхронизирует все компоненты."""
    
    def __init__(self, 
                 market_engine: MarketEngine,
                 broker: Broker,
                 state_manager: StateManager,
                 tick_duration_seconds: float = 0.5):
        """
        Args:
            market_engine: Market Engine
            broker: Broker
            state_manager: State Manager
            tick_duration_seconds: Длительность одного тика
        """
        self.market_engine = market_engine
        self.broker = broker
        self.state_manager = state_manager
        self.tick_duration_seconds = tick_duration_seconds
        
        self.is_running = False
        self.tick_count = 0
        self.listeners = []

        self.event_manager = EventManager(config_path="config/events_config.json")
    
    def add_listener(self, callback):
        """Добавляет слушателя для обновлений."""
        self.listeners.append(callback)
    
    async def broadcast_update(self, data: Dict[str, Any]):
        """Отправляет обновление всем слушателям."""
        for listener in self.listeners:
            try:
                await listener(data)
            except Exception as e:
                print(f"Error broadcasting to listener: {e}")
    
    async def run(self):
        """Главный цикл симуляции."""
        print("\n" + "=" * 80)
        print("ORCHESTRATOR: ЗАПУСК ГЛАВНОГО ЦИКЛА")
        print("=" * 80)
        
        self.is_running = True
        
        try:
            while True:  # Бесконечный цикл для поддержки паузы/возобновления
                # Если на паузе, ждём пока возобновят
                while not self.is_running:
                    await asyncio.sleep(0.1)
                
                self.event_manager.check_and_trigger(self.market_engine.tick_count, self.market_engine)
                # 1. Один тик рынка
                dividends = self.market_engine.tick()  # Получаем дивиденды
                self.tick_count += 1
                
                # 1.5. НОВОЕ: Применяем дивиденды сразу (они выплачиваются по расписанию компаний)
                if dividends:
                    self.broker.apply_dividends(dividends)
                
                # 2. Получаем цены и волатильности
                prices = {
                    ticker: company.price
                    for ticker, company in self.market_engine.companies.items()
                    if not company.is_index
                }
                
                volatilities = {
                    ticker: company.volatility
                    for ticker, company in self.market_engine.companies.items()
                    if not company.is_index
                }
                
                # 3. Проверяем маржу и ликвидируем
                liquidations = self.broker.check_liquidations(prices, volatilities)
                
                if liquidations:
                    print(f"\n[Тик {self.market_engine.tick_count}] ⚠️  ЛИКВИДАЦИИ:")
                    for username, info in liquidations.items():
                        print(f"  {username}: УДС={info['uds']:.2f}")
                
                # 4. Отправляем обновления через WebSocket
                await self.broadcast_update({
                    "tick": self.market_engine.tick_count,
                    "index_price": self.market_engine.index_price,
                    "prices": prices,
                    "liquidations": liquidations
                })
                
                # 5. Конец дня (каждые 24 тика)
                if self.market_engine.tick_count % 24 == 0:
                    print(f"\n[День {self.market_engine.tick_count // 24}]")
                    
                    # Дневные операции
                    self.broker.on_daily_tick(prices, volatilities)
                    print(f"  ✓ Дневные операции завершены")
                    
                    # Сохраняем состояние
                    self.state_manager.save_simulation_state(
                        self.market_engine,
                        self.broker,
                        verbose=False
                    )
                    print(f"  ✓ Состояние сохранено")
                
                # 6. Конец недели (каждые 168 тиков)
                if self.market_engine.tick_count % 168 == 0 and self.market_engine.tick_count > 0:
                    self.broker.on_weekly_tick(prices)
                    print(f"  ✓ Недельные операции завершены")
                
                # 7. Ждём перед следующим тиком
                await asyncio.sleep(self.tick_duration_seconds)
        
        except KeyboardInterrupt:
            print("\n✓ Симуляция прервана пользователем")
        except Exception as e:
            print(f"\n✗ Ошибка в Main Loop: {e}")
            raise
        finally:
            # Финальное сохранение
            print("\nФинальное сохранение состояния...")
            self.state_manager.save_simulation_state(
                self.market_engine,
                self.broker,
                verbose=False
            )
            print("✓ Симуляция завершена")
    
    def pause(self):
        """Приостанавливает симуляцию."""
        self.is_running = False
    
    def resume(self):
        """Возобновляет симуляцию."""
        self.is_running = True
    
    async def step(self):
        """Один шаг симуляции (для пошагового запуска)."""
        if not self.is_running:
            self.is_running = True
        
        self.market_engine.tick()
        self.tick_count += 1
        
        prices = {
            ticker: company.price
            for ticker, company in self.market_engine.companies.items()
            if not company.is_index
        }
        
        volatilities = {
            ticker: company.volatility
            for ticker, company in self.market_engine.companies.items()
            if not company.is_index
        }
        
        self.broker.check_liquidations(prices, volatilities)
        
        if self.market_engine.tick_count % 24 == 0:
            self.broker.on_daily_tick(prices, volatilities)
            self.state_manager.save_simulation_state(
                self.market_engine,
                self.broker,
                verbose=False
            )