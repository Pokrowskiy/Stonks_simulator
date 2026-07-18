"""
REST API эндпоинты для Broker.
Управление счётами, ордерами, информация о портфелях.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from broker import Broker, Order, OrderExecutionError


# ===== Pydantic модели для ответов =====

class OrderRequest(BaseModel):
    """Запрос на выполнение ордера."""
    username: str
    ticker: str
    action: str  # "BUY" или "SELL"
    quantity: int


class OrderResponse(BaseModel):
    """Ответ на ордер."""
    order_id: str
    status: str  # "EXECUTED" или "REJECTED"
    rejection_reason: Optional[str] = None
    commission: float


class Position(BaseModel):
    """Позиция в портфеле."""
    ticker: str
    quantity: int
    entry_price: float
    current_price: float
    position_value: float


class AccountMargins(BaseModel):
    """Информация о маржах."""
    initial_margin: float
    min_margin: float


class AccountPnL(BaseModel):
    """Информация о прибыли/убытке."""
    daily_pnl: float
    daily_pnl_percent: float
    weekly_pnl: float
    total_pnl: float
    total_return_percent: float


class AccountSummary(BaseModel):
    """Полная сводка по счёту."""
    username: str
    uds: float
    uds_status: str
    balances: Dict[str, float]
    margins: AccountMargins
    pnl: AccountPnL
    positions: List[Position]
    is_liquidated: bool


class CreateAccountRequest(BaseModel):
    """Запрос на создание счёта."""
    username: str
    initial_balance: float


class CreateAccountResponse(BaseModel):
    """Ответ: счёт создан."""
    username: str
    initial_balance: float
    status: str


def create_broker_router(broker: Broker, market_engine: Any) -> APIRouter:
    """
    Создаёт router для Broker.
    
    Args:
        broker: Экземпляр Broker
        market_engine: Экземпляр MarketEngine (для получения цен)
        
    Returns:
        APIRouter с эндпоинтами
    """
    router = APIRouter(prefix="/api/broker", tags=["Broker"])
    
    # ===== POST /api/broker/create-account =====
    @router.post(
        "/create-account",
        response_model=CreateAccountResponse,
        summary="Создать новый счёт",
        description="Создаёт новый инвестиционный счёт с начальным балансом"
    )
    def create_account(request: CreateAccountRequest):
        """Создаёт новый счёт."""
        try:
            account = broker.create_account(
                username=request.username,
                initial_balance=request.initial_balance
            )
            
            return CreateAccountResponse(
                username=account.username,
                initial_balance=account.start_value,
                status="created"
            )
        
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при создании счёта: {str(e)}"
            )
    
    # ===== GET /api/broker/account/{username} =====
    @router.get(
        "/account/{username}",
        response_model=AccountSummary,
        summary="Получить информацию о счёте",
        description="Полная сводка: баланс, позиции, маржа, УДС, PnL"
    )
    def get_account(username: str):
        """Возвращает полную информацию о счёте."""
        try:
            # Получаем цены от Market Engine
            prices = {
                ticker: company.price
                for ticker, company in market_engine.companies.items()
                if not company.is_index
            }
            
            # Получаем волатильности
            volatilities = {
                ticker: company.volatility
                for ticker, company in market_engine.companies.items()
                if not company.is_index
            }
            
            summary = broker.get_account_summary(username, prices, volatilities)
            
            return AccountSummary(
                username=summary["username"],
                uds=summary["uds"],
                uds_status=summary["uds_status"],
                balances=summary["balances"],
                margins=AccountMargins(
                    initial_margin=summary["margins"]["initial_margin"],
                    min_margin=summary["margins"]["min_margin"]
                ),
                pnl=AccountPnL(
                    daily_pnl=summary["pnl"]["daily_pnl"],
                    daily_pnl_percent=summary["pnl"]["daily_pnl_percent"],
                    weekly_pnl=summary["pnl"]["weekly_pnl"],
                    total_pnl=summary["pnl"]["total_pnl"],
                    total_return_percent=summary["pnl"]["total_return_percent"],
                ),
                positions=[
                    Position(
                        ticker=pos["ticker"],
                        quantity=pos["quantity"],
                        entry_price=pos["entry_price"],
                        current_price=pos["current_price"],
                        position_value=pos["position_value"],
                    )
                    for pos in summary["positions"]
                ],
                is_liquidated=summary["is_liquidated"],
            )
        
        except ValueError as e:
            raise HTTPException(
                status_code=404,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при получении информации о счёте: {str(e)}"
            )
    
    # ===== GET /api/broker/accounts =====
    @router.get(
        "/accounts",
        summary="Получить сводку по всем счётам",
        description="Информация по всем пользователям (для админов)"
    )
    def get_all_accounts():
        """Возвращает сводку по всем счётам."""
        try:
            prices = {
                ticker: company.price
                for ticker, company in market_engine.companies.items()
                if not company.is_index
            }
            
            volatilities = {
                ticker: company.volatility
                for ticker, company in market_engine.companies.items()
                if not company.is_index
            }
            
            summaries = broker.get_all_accounts_summary(prices, volatilities)
            
            return {
                "total_accounts": len(summaries),
                "accounts": summaries
            }
        
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при получении счётов: {str(e)}"
            )
    
    # ===== POST /api/broker/order =====
    @router.post(
        "/order",
        response_model=OrderResponse,
        summary="Выполнить ордер",
        description="Покупка или продажа актива. Проверяется маржа и УДС."
    )
    def execute_order(request: OrderRequest):
        """Выполняет ордер (покупка/продажа)."""
        try:
            # Получаем текущую цену актива
            company = market_engine.get_company(request.ticker)
            if not company:
                raise HTTPException(
                    status_code=404,
                    detail=f"Актив {request.ticker} не найден"
                )
            
            current_price = company.price
            
            # Получаем волатильности
            volatilities = {
                ticker: c.volatility
                for ticker, c in market_engine.companies.items()
                if not c.is_index
            }
            
            # Выполняем ордер
            order = broker.execute_order(
                username=request.username,
                ticker=request.ticker,
                action=request.action,
                quantity=request.quantity,
                current_price=current_price,
                volatilities=volatilities
            )
            
            return OrderResponse(
                order_id=order.order_id,
                status=order.status,
                rejection_reason=order.rejection_reason,
                commission=round(order.commission, 2)
            )
        
        except OrderExecutionError as e:
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при выполнении ордера: {str(e)}"
            )
    
    # ===== GET /api/broker/order-history/{username} =====
    @router.get(
        "/order-history/{username}",
        summary="История ордеров пользователя",
        description="Список всех ордеров (выполненных и отклонённых)"
    )
    def get_order_history(
        username: str,
        limit: int = Query(50, ge=1, le=500, description="Максимум последних ордеров")
    ):
        """Возвращает историю ордеров пользователя."""
        try:
            orders = broker.get_order_history(username, limit)
            
            return {
                "username": username,
                "total": len(orders),
                "orders": [o.to_dict() for o in orders]
            }
        
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при получении истории: {str(e)}"
            )
    
    # ===== GET /api/broker/status =====
    @router.get(
        "/status",
        summary="Статус брокера",
        description="Техническая информация"
    )
    def get_broker_status():
        """Возвращает статус Брокера."""
        try:
            return {
                "status": "running",
                "total_accounts": len(broker.accounts),
                "total_liquidated": sum(
                    1 for a in broker.accounts.values() if a.is_liquidated
                ),
                "total_orders": len(broker.order_history),
                "commission_trade": broker.commission_trade,
                "commission_leverage_daily": broker.commission_leverage_daily,
            }
        
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при получении статуса: {str(e)}"
            )
    
    # ===== GET /api/broker/liquidations =====
    @router.get(
        "/liquidations",
        summary="Ликвидированные счёта",
        description="Список счётов, прошедших маржин-колл"
    )
    def get_liquidations():
        """Возвращает список ликвидированных счётов."""
        try:
            liquidated = [
                {
                    "username": account.username,
                    "cash_balance": account.cash_balance,
                    "liquidation_info": account.liquidation_info
                }
                for account in broker.accounts.values()
                if account.is_liquidated
            ]
            
            return {
                "total_liquidated": len(liquidated),
                "accounts": liquidated
            }
        
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при получении ликвидаций: {str(e)}"
            )
    
    return router