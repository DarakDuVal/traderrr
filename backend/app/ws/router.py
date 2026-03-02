"""
WebSocket endpoint — /ws?token=<jwt>

Provides real-time signal and price streaming.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from jose import JWTError

from app.auth.service import decode_token
from config.settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self) -> None:
        # user_id → set of active websockets
        self._connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int) -> None:
        await websocket.accept()
        self._connections.setdefault(user_id, set()).add(websocket)
        logger.info("WS connected: user_id=%s", user_id)

    def disconnect(self, websocket: WebSocket, user_id: int) -> None:
        conns = self._connections.get(user_id)
        if conns:
            conns.discard(websocket)
            if not conns:
                del self._connections[user_id]
        logger.info("WS disconnected: user_id=%s", user_id)

    async def broadcast(self, message: dict) -> None:
        """Send a message to all connected clients."""
        payload = json.dumps(message)
        for conns in self._connections.values():
            for ws in list(conns):
                try:
                    await ws.send_text(payload)
                except Exception:
                    pass

    async def send_to_user(self, user_id: int, message: dict) -> None:
        """Send a message to a specific user."""
        payload = json.dumps(message)
        for ws in list(self._connections.get(user_id, [])):
            try:
                await ws.send_text(payload)
            except Exception:
                pass


manager = ConnectionManager()


def _make_message(msg_type: str, payload: dict | None = None) -> dict:
    return {
        "type": msg_type,
        "payload": payload or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.websocket("/ws")  # type: ignore[misc, untyped-decorator]
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint with JWT query-parameter authentication
    and 30 s ping/pong keepalive.
    """
    settings = get_settings()
    token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    try:
        payload = decode_token(token, settings.SECRET_KEY)
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        await websocket.close(code=4001, reason="Invalid token")
        return

    await manager.connect(websocket, user_id)

    async def _keepalive() -> None:
        """Send ping every 30 seconds."""
        try:
            while True:
                await asyncio.sleep(30)
                await websocket.send_text(json.dumps(_make_message("ping")))
        except Exception:
            pass

    keepalive_task = asyncio.create_task(_keepalive())

    try:
        while True:
            data = await websocket.receive_text()
            # clients may send pong or other messages — just log
            logger.debug("WS recv user_id=%s: %s", user_id, data[:200])
    except WebSocketDisconnect:
        pass
    finally:
        keepalive_task.cancel()
        manager.disconnect(websocket, user_id)
