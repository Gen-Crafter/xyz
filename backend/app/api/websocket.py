import json
import asyncio
import logging
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for real-time event streaming."""

    def __init__(self):
        self._channels: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, channel: str, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            if channel not in self._channels:
                self._channels[channel] = set()
            self._channels[channel].add(websocket)
        logger.info("WebSocket connected to channel: %s", channel)

    async def disconnect(self, channel: str, websocket: WebSocket):
        async with self._lock:
            if channel in self._channels:
                self._channels[channel].discard(websocket)
                if not self._channels[channel]:
                    del self._channels[channel]
        logger.info("WebSocket disconnected from channel: %s", channel)

    async def broadcast(self, channel: str, data: dict):
        async with self._lock:
            connections = self._channels.get(channel, set()).copy()
        dead = []
        for ws in connections:
            try:
                await ws.send_text(json.dumps(data, default=str))
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._channels.get(channel, set()).discard(ws)

    async def handle_connection(self, channel: str, websocket: WebSocket):
        await self.connect(channel, websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            await self.disconnect(channel, websocket)
        except Exception:
            await self.disconnect(channel, websocket)
