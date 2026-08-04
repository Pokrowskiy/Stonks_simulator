"""
Admin API: эндпоинты для администраторов симуляции.

Позволяет управлять симуляцией, вбрасывать события, корректировать балансы,
контролировать скорость и статус системы.

Все эти эндпоинты доступны только администраторам (в реальном приложении
должна быть проверка API ключа или токена).
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Any, Optional


# ===== Pydantic модели =====

class SpeedRequest(BaseModel):
    """Запрос на изменение скорости симуляции."""
    tick_duration_seconds: float


class EventInjectionRequest(BaseModel):
    """Запрос на вброс события на рынок."""
    name: str
    description: Optional[str] = None
    target_type: str  # "company", "sector", "market", "trend"
    target: str  # ticker для company, название для sector, "MARKET" для market, ticker для trend
    impact_profit: float = 0.0  # Влияние на прибыль (множитель) или strength для trend
    impact_volatility: float = 0.0  # Влияние на волатильность (множитель)
    trend_direction: Optional[str] = None  # "UP" или "DOWN" для trend-событий
    decay_type: str = "linear"  # "linear" или "shock"
    duration_ticks: int = 24  # Длительность события в тиках


class BalanceAdjustmentRequest(BaseModel):
    """Запрос на корректировку баланса пользователя."""
    username: str
    amount: float  # Положительное число = пополнение, отрицательное = списание
    reason: Optional[str] = None  # Причина корректировки


class SimulationStateResponse(BaseModel):
    """Состояние симуляции."""
    is_running: bool
    tick_count: int
    tick_duration_seconds: float
    index_price: float
    total_accounts: int
    liquidated_accounts: int


def create_admin_router(orchestrator: Any) -> APIRouter:
    """
    Создаёт router для Admin API.
    
    Args:
        orchestrator: Экземпляр Main Loop оркестратора
        
    Returns:
        APIRouter с административными эндпоинтами
    """
    router = APIRouter(prefix="/api/admin", tags=["Admin"])
    
    # ===== УПРАВЛЕНИЕ СИМУЛЯЦИЕЙ =====
    
    @router.post(
        "/start",
        summary="Запустить симуляцию",
        description="Запускает основной цикл симуляции"
    )
    async def start_simulation():
        """Запускает симуляцию."""
        try:
            if orchestrator.is_running:
                raise HTTPException(
                    status_code=400,
                    detail="Симуляция уже запущена"
                )
            
            orchestrator.resume()
            
            return {
                "status": "started",
                "message": "Симуляция запущена"
            }
        
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при запуске: {str(e)}"
            )
    
    @router.post(
        "/pause",
        summary="Пауза симуляции",
        description="Приостанавливает выполнение симуляции"
    )
    async def pause_simulation():
        """Приостанавливает симуляцию."""
        try:
            if not orchestrator.is_running:
                raise HTTPException(
                    status_code=400,
                    detail="Симуляция уже на паузе"
                )
            
            orchestrator.pause()
            
            return {
                "status": "paused",
                "message": "Симуляция поставлена на паузу",
                "current_tick": orchestrator.market_engine.tick_count
            }
        
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при паузе: {str(e)}"
            )
    
    @router.get(
        "/status",
        response_model=SimulationStateResponse,
        summary="Статус симуляции",
        description="Получить полное состояние симуляции"
    )
    async def get_simulation_status():
        """Возвращает статус симуляции."""
        try:
            return SimulationStateResponse(
                is_running=orchestrator.is_running,
                tick_count=orchestrator.market_engine.tick_count,
                tick_duration_seconds=orchestrator.tick_duration_seconds,
                index_price=orchestrator.market_engine.index_price,
                total_accounts=len(orchestrator.broker.accounts),
                liquidated_accounts=sum(
                    1 for a in orchestrator.broker.accounts.values()
                    if a.is_liquidated
                )
            )
        
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при получении статуса: {str(e)}"
            )
    
    # ===== УПРАВЛЕНИЕ СКОРОСТЬЮ =====
    
    @router.post(
        "/speed",
        summary="Установить скорость тика",
        description="Меняет длительность одного тика (от 0.1 до 10 секунд)"
    )
    async def set_tick_speed(request: SpeedRequest):
        """Устанавливает скорость тика."""
        try:
            if request.tick_duration_seconds < 0.1 or request.tick_duration_seconds > 10.0:
                raise HTTPException(
                    status_code=400,
                    detail="Скорость должна быть между 0.1 и 10 секундами"
                )
            
            old_speed = orchestrator.tick_duration_seconds
            orchestrator.tick_duration_seconds = request.tick_duration_seconds
            
            return {
                "status": "updated",
                "old_speed": old_speed,
                "new_speed": request.tick_duration_seconds,
                "message": f"Скорость изменена с {old_speed:.2f}s на {request.tick_duration_seconds:.2f}s"
            }
        
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при изменении скорости: {str(e)}"
            )
    
    @router.get(
        "/speed",
        summary="Получить текущую скорость",
        description="Возвращает длительность текущего тика"
    )
    async def get_tick_speed():
        """Возвращает текущую скорость тика."""
        return {
            "tick_duration_seconds": orchestrator.tick_duration_seconds,
            "ticks_per_minute": 60 / orchestrator.tick_duration_seconds
        }
    
    # ===== УПРАВЛЕНИЕ СОБЫТИЯМИ =====
    
    @router.post(
        "/inject-event",
        summary="Вбросить событие на рынок",
        description="Добавляет новое событие, которое повлияет на цены и волатильность"
    )
    async def inject_event(request: EventInjectionRequest):
        """Добавляет событие на рынок."""
        try:
            import uuid
            from src.market_engine.market import NewsEvent, TrendEvent
            
            # Если это тренд-событие
            if request.target_type == "trend":
                event = TrendEvent(
                    event_id=str(uuid.uuid4()),
                    name=request.name,
                    target_value=request.target,
                    trend_direction=request.trend_direction or "UP",
                    strength=request.impact_profit,  # Переиспользуем поле для strength
                    duration_ticks=request.duration_ticks
                )
                orchestrator.market_engine.add_trend_event(event)
            else:
                # Обычное новостное событие
                event = NewsEvent(
                    event_id=str(uuid.uuid4()),
                    name=request.name,
                    target_type=request.target_type,
                    target_value=request.target,
                    impact_profit=request.impact_profit,
                    impact_volatility=request.impact_volatility,
                    duration_ticks=request.duration_ticks,
                    decay_type=request.decay_type
                )
                orchestrator.market_engine.add_event(event)
            
            return {
                "status": "injected",
                "event_id": event.event_id,
                "event_name": event.name,
                "target": f"{request.target_type}:{request.target}",
                "duration_ticks": request.duration_ticks,
                "message": f"Событие '{request.name}' успешно добавлено на рынок"
            }
        
        except Exception as e:
            print(f"Error injecting event: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при вбросе события: {str(e)}"
            )
    
    @router.get(
        "/events",
        summary="Получить все активные события",
        description="Возвращает список всех текущих событий на рынке"
    )
    async def get_active_events():
        """Возвращает активные события."""
        try:
            events_data = []
            
            for event in orchestrator.market_engine.events:
                ticks_remaining = event.end_tick - orchestrator.market_engine.tick_count
                current_impact = event.get_current_impact()
                
                events_data.append({
                    "id": event.id,
                    "name": event.name,
                    "target": event.target,
                    "ticks_remaining": ticks_remaining,
                    "impact_profit": current_impact["profit"],
                    "impact_volatility": current_impact["volatility"],
                    "progress_percent": (1 - ticks_remaining / event.duration_ticks) * 100
                })
            
            return {
                "total_active": len(events_data),
                "events": events_data
            }
        
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при получении событий: {str(e)}"
            )
    
    # ===== УПРАВЛЕНИЕ БАЛАНСАМИ =====
    
    @router.post(
        "/adjust-balance",
        summary="Корректировать баланс пользователя",
        description="Пополнить или списать средства со счёта пользователя"
    )
    async def adjust_balance(request: BalanceAdjustmentRequest):
        """Корректирует баланс пользователя."""
        try:
            account = orchestrator.broker.get_account(request.username)
            
            if not account:
                raise HTTPException(
                    status_code=404,
                    detail=f"Счёт {request.username} не найден"
                )
            
            old_balance = account.cash_balance
            account.cash_balance += request.amount
            new_balance = account.cash_balance
            
            return {
                "status": "adjusted",
                "username": request.username,
                "old_balance": old_balance,
                "adjustment": request.amount,
                "new_balance": new_balance,
                "reason": request.reason or "Manual adjustment by admin",
                "message": f"Баланс {request.username} изменён на ${request.amount:.2f}"
            }
        
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при корректировке баланса: {str(e)}"
            )
    
    # ===== СБРОС И ВОССТАНОВЛЕНИЕ =====
    
    @router.post(
        "/reset",
        summary="Сброс симуляции",
        description="Удаляет все сохранения и перезагружает симуляцию с нуля"
    )
    async def reset_simulation():
        """Сбрасывает симуляцию."""
        try:
            if orchestrator.is_running:
                orchestrator.is_running = False
            
            # Удаляем сохранения
            orchestrator.state_manager.reset_simulation()
            
            return {
                "status": "reset",
                "message": "Симуляция сброшена. Пожалуйста, перезагрузите приложение."
            }
        
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при сбросе: {str(e)}"
            )
    
    # ===== ДИАГНОСТИКА =====
    
    @router.get(
        "/health",
        summary="Проверка здоровья системы",
        description="Возвращает информацию о статусе всех компонентов"
    )
    async def health_check():
        """Проверяет здоровье системы."""
        try:
            return {
                "status": "healthy",
                "components": {
                    "market_engine": "ok",
                    "broker": "ok",
                    "state_manager": "ok",
                    "orchestrator": "running" if orchestrator.is_running else "paused"
                },
                "timestamp": orchestrator.market_engine.tick_count
            }
        
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"System is unhealthy: {str(e)}"
            )
    
    @router.post(
        "/save-state",
        summary="Сохранить состояние",
        description="Вручную сохраняет текущее состояние в файлы"
    )
    async def save_state_manually():
        """Сохраняет состояние вручную."""
        try:
            orchestrator.state_manager.save_simulation_state(
                orchestrator.market_engine,
                orchestrator.broker,
                verbose=True
            )
            
            return {
                "status": "saved",
                "tick": orchestrator.market_engine.tick_count,
                "message": "Состояние успешно сохранено"
            }
        
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при сохранении: {str(e)}"
            )
    
    return router