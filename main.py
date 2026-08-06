"""
Trading Simulator: главный файл приложения.
"""

import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

from src.state_manager.state_manager import StateManager
from src.state_manager.state_manager_config import StateManagerConfig
from src.orchestrator.main_loop import Orchestrator
from src.api.market_api import create_market_router
from src.api.broker_api import create_broker_router
from src.api.admin_api import create_admin_router
from src.api.websocket import ws_manager, websocket_handler


from fastapi.middleware.cors import CORSMiddleware

# ===== Инициализация =====

print("\n" + "=" * 80)
print("TRADING SIMULATOR: ИНИЦИАЛИЗАЦИЯ")
print("=" * 80)

# State Manager
print("\n[1] Инициализация State Manager...")
state_manager = StateManager(StateManagerConfig)

# Загружаем состояние (из сохранений или конфига)
print("\n[2] Загрузка состояния...")
market_engine, broker, metadata = state_manager.load_simulation_state()

# Оркестратор
print("\n[3] Инициализация Orchestrator...")
orchestrator = Orchestrator(market_engine, broker, state_manager)

# Подключаем WebSocket менеджер к оркестратору
async def broadcast_tick_update(data):
    await ws_manager.broadcast(data)

orchestrator.add_listener(broadcast_tick_update)

# FastAPI приложение
print("\n[4] Инициализация FastAPI приложение...")
app = FastAPI(
    title="Trading Simulator API",
    description="REST API для биржевого симулятора",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== REST API Маршруты =====

print("\n[5] Подключение REST API маршрутов...")

market_router = create_market_router(market_engine)
broker_router = create_broker_router(broker, market_engine)
admin_router = create_admin_router(orchestrator)

app.include_router(market_router)
app.include_router(broker_router)
app.include_router(admin_router)

print("  ✓ Market API подключена")
print("  ✓ Broker API подключена")
print("  ✓ Admin API подключена")

# ===== Корневые маршруты =====

@app.get("/", response_class=HTMLResponse)
async def root_html():
    """Главная страница - выбор интерфейса."""
    return """
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #1a1a1a;
                color: white;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            .container {
                text-align: center;
            }
            h1 {
                margin-bottom: 40px;
                font-size: 32px;
            }
            .buttons {
                display: flex;
                gap: 20px;
                justify-content: center;
            }
            a {
                display: inline-block;
                padding: 15px 40px;
                background: #333;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                font-size: 16px;
                font-weight: 500;
                transition: background 0.2s;
            }
            a:hover {
                background: #555;
            }
            a.api {
                background: #666;
            }
            a.api:hover {
                background: #888;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Trading Simulator</h1>
            <div class="buttons">
                <a href="/trader">Trader</a>
                <a href="/admin">Admin</a>
                <a href="/docs" class="api">API Docs</a>
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/trader", response_class=HTMLResponse)
async def trader_html():
    """Пользовательский интерфейс."""
    try:
        with open("frontend/trader.html", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "<html><body><h1>Error: trader.html not found</h1></body></html>"

@app.get("/admin", response_class=HTMLResponse)
async def admin_html():
    """Админский интерфейс."""
    try:
        with open("frontend/admin.html", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "<html><body><h1>Error: admin.html not found</h1></body></html>"

@app.get("/health")
async def health():
    """Проверка здоровья."""
    return {
        "status": "healthy",
        "market_engine": "ok",
        "broker": "ok",
        "orchestrator": "ready"
    }



# ===== WebSocket =====

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_handler(websocket)

# ===== Startup/Shutdown =====

@app.on_event("startup")
async def startup():
    """Запуск Main Loop при старте."""
    print("\n[6] Запуск Main Loop...")
    print("=" * 80)
    
    # Запускаем Main Loop в фоновом потоке
    asyncio.create_task(orchestrator.run())

@app.on_event("shutdown")
async def shutdown():
    """Завершение при выключении."""
    print("\n✓ Trading Simulator завершил работу")

# ===== Запуск =====

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("✓ Trading Simulator готов к запуску")
    print("=" * 80)
    print("\nЗапуск на http://localhost:8020")
    print("Документация: http://localhost:8020/docs")
    print("\nДля остановки: Ctrl+C")
    print("=" * 80 + "\n")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8020,
        reload=False,
        log_level="info"
    )