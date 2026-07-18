"""
REST API эндпоинты для Market Engine.
Предоставляет доступ к рыночным данным через FastAPI.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json

class CompanySnapshot(BaseModel):
    """Снимок состояния компании для списка."""
    ticker: str
    name: str
    description: str
    sectors: List[str]
    price_current: float
    price_day_start: float
    price_change_percent: float
    volatility: float


class CompanyHistoryResponse(BaseModel):
    """История цен компании."""
    ticker: str
    name: str
    history: List[float]
    limit: int
    total_available: int


class CompanyFundamentals(BaseModel):
    """Фундаментальные данные компании."""
    ticker: str
    name: str
    profit_current: float
    profit_base: float
    profit_last_dividend: float
    profit_growth: float
    dividend_payout_ratio: float
    payout_period_ticks: int
    ticks_to_next_payout: int
    dividend_per_share_next: float


class MarketIndex(BaseModel):
    """Данные рыночного индекса."""
    index_price: float
    index_change_percent: float
    index_history_last_24h: List[float]
    total_companies: int


class DividendEventResponse(BaseModel):
    """Событие выплаты дивиденда."""
    ticker: str
    dividend_per_share: float
    payment_date_tick: int


class ErrorResponse(BaseModel):
    """Ошибка API."""
    error: str
    details: Optional[str] = None


def create_market_router(market_engine: Any) -> APIRouter:
    router = APIRouter(prefix="/api/market", tags=["Market Data"])
    
    # ===== GET /api/market/companies =====
    @router.get(
        "/companies",
        response_model=List[CompanySnapshot],
        summary="Получить список всех компаний",
        description="Возвращает сводку по всем компаниям на рынке: текущие цены, изменения, волатильность"
    )
    def get_all_companies():
        """
        Возвращает список всех компаний со сводкой.
        Используется при загрузке дашборда.
        """
        try:
            companies = []
            
            for ticker, company in market_engine.companies.items():
                if company.is_index:
                    continue  # Индекс отдельно

                price_day_start = company.price_history[0] if company.price_history else company.price
                price_change_percent = ((company.price - price_day_start) / price_day_start * 100) if price_day_start > 0 else 0
                
                companies.append(CompanySnapshot(
                    ticker=ticker,
                    name=company.name,
                    description=company.description,
                    sectors=company.sectors,
                    price_current=round(company.price, 2),
                    price_day_start=round(price_day_start, 2),
                    price_change_percent=round(price_change_percent, 2),
                    volatility=company.volatility
                ))
            
            companies.sort(key=lambda x: x.ticker)
            return companies
        
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при получении списка компаний: {str(e)}"
            )
    
    # ===== GET /api/market/history/{ticker} =====
    @router.get(
        "/history/{ticker}",
        response_model=CompanyHistoryResponse,
        summary="Получить историю цен компании",
        description="Возвращает массив исторических цен для построения графиков"
    )
    def get_company_history(
        ticker: str,
        limit: int = Query(48, ge=1, le=1000, description="Максимум последних N цен")
    ):
        """
        Возвращает историю цен компании.
        
        Args:
            ticker: Тикер компании (например, "GIGA")
            limit: Сколько последних точек вернуть (по умолчанию 48, макс 1000)
        """
        company = market_engine.get_company(ticker)
        
        if not company:
            raise HTTPException(
                status_code=404,
                detail=f"Компания с тикером '{ticker}' не найдена"
            )
        
        if company.is_index:
            raise HTTPException(
                status_code=400,
                detail="Индекс не имеет истории цен (используйте /api/market/index)"
            )
        
        try:
            history = company.price_history[-limit:] if company.price_history else []
            
            return CompanyHistoryResponse(
                ticker=ticker,
                name=company.name,
                history=[round(p, 2) for p in history],
                limit=limit,
                total_available=len(company.price_history)
            )
        
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при получении истории: {str(e)}"
            )
    
    # ===== GET /api/market/fundamentals/{ticker} =====
    @router.get(
        "/fundamentals/{ticker}",
        response_model=CompanyFundamentals,
        summary="Получить фундаментальные данные",
        description="Глубокая аналитика компании: прибыль, дивиденды"
    )
    def get_fundamentals(ticker: str):
        """
        Возвращает фундаментальные данные компании.
        Используется для ИИ-Аналитика и детального анализа.
        
        Args:
            ticker: Тикер компании
        """
        company = market_engine.get_company(ticker)
        
        if not company:
            raise HTTPException(
                status_code=404,
                detail=f"Компания с тикером '{ticker}' не найдена"
            )
        
        try:
            dividend_next = company.calc_dividend_amount()
            
            return CompanyFundamentals(
                ticker=ticker,
                name=company.name,
                profit_current=round(company.profit_current, 2),
                profit_base=round(company.profit_base, 2),
                profit_last_dividend=round(company.profit_last_dividend, 2),
                profit_growth=company.profit_growth,
                dividend_payout_ratio=company.div_payout_ratio,
                payout_period_ticks=company.div_period_ticks,
                ticks_to_next_payout=company.ticks_to_next_dividend,
                dividend_per_share_next=round(dividend_next, 4)
            )
        
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при получении фундаментальных данных: {str(e)}"
            )
    
    # ===== GET /api/market/index =====
    @router.get(
        "/index",
        response_model=MarketIndex,
        summary="Получить данные рыночного индекса",
        description="Средняя цена всех компаний, история индекса"
    )
    def get_market_index():
        """
        Возвращает данные рыночного индекса.
        Индекс = средняя цена всех компаний.
        """
        try:
            if not market_engine.index_history or len(market_engine.index_history) == 0:
                raise ValueError("История индекса пуста")
            
            # Рассчитываем изменение за последние 24 тика (1 день)
            index_24h_ago = market_engine.index_history[-24] if len(market_engine.index_history) >= 24 else market_engine.index_history[0]
            index_change_percent = ((market_engine.index_price - index_24h_ago) / index_24h_ago * 100) if index_24h_ago > 0 else 0
            
            # История за последние 24 часа (тика)
            index_last_24h = market_engine.index_history[-24:] if market_engine.index_history else []
            
            non_index_count = sum(1 for c in market_engine.companies.values() if not c.is_index)
            
            return MarketIndex(
                index_price=round(market_engine.index_price, 2),
                index_change_percent=round(index_change_percent, 2),
                index_history_last_24h=[round(p, 2) for p in index_last_24h],
                total_companies=non_index_count
            )
        
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при получении индекса: {str(e)}"
            )
    
    # ===== GET /api/market/status =====
    @router.get(
        "/status",
        summary="Получить статус рынка",
        description="Техническая информация о состоянии Engine"
    )
    def get_market_status():
        """Возвращает техническую информацию о рынке."""
        try:
            return {
                "status": "running",
                "tick_count": market_engine.tick_count,
                "total_companies": len([c for c in market_engine.companies.values() if not c.is_index]),
                "active_events": len(market_engine.events),
                "index_price": round(market_engine.index_price, 2),
            }
        
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при получении статуса: {str(e)}"
            )
    
    # ===== GET /api/market/events =====
    @router.get(
        "/events",
        summary="Получить активные события",
        description="Список текущих новостей и событий на рынке"
    )
    def get_active_events():
        """Возвращает список активных событий (новостей)."""
        try:
            events = []
            for event in market_engine.events:
                impact = event.get_current_impact()
                events.append({
                    "event_id": event.event_id,
                    "name": event.name,
                    "target_type": event.target_type,
                    "target_value": event.target_value,
                    "remaining_ticks": event.remaining_ticks,
                    "duration_ticks": event.duration_ticks,
                    "impact_current": round(impact, 2),
                })
            
            return {
                "total_active": len(events),
                "events": events
            }
        
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при получении событий: {str(e)}"
            )
    return router