"""
WebSocket: потоковые обновления для фронтенда.
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Set
import json


class WebSocketManager:
    """Управляет WebSocket подключениями."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """Принимает новое подключение."""
        await websocket.accept()
        self.active_connections.add(websocket)
        print(f"✓ WebSocket подключен ({len(self.active_connections)} клиентов)")
    
    async def disconnect(self, websocket: WebSocket):
        """Отключает клиента."""
        self.active_connections.discard(websocket)
        print(f"✓ WebSocket отключен ({len(self.active_connections)} клиентов)")
    
    async def broadcast(self, data: dict):
        """Отправляет данные всем подключённым клиентам."""
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                disconnected.add(connection)
        
        # Удаляем отключённых
        for conn in disconnected:
            self.active_connections.discard(conn)


# Глобальный менеджер
ws_manager = WebSocketManager()


async def websocket_handler(websocket: WebSocket):
    """Обработчик WebSocket."""
    await ws_manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await ws_manager.disconnect(websocket)