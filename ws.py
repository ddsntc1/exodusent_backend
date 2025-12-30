from collections import defaultdict
from typing import DefaultDict, Set

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._channels: DefaultDict[int, Set[WebSocket]] = defaultdict(set)

    async def connect(self, poll_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._channels[poll_id].add(websocket)

    def disconnect(self, poll_id: int, websocket: WebSocket) -> None:
        self._channels[poll_id].discard(websocket)
        if not self._channels[poll_id]:
            self._channels.pop(poll_id, None)

    async def broadcast(self, poll_id: int, payload: dict) -> None:
        websockets = list(self._channels.get(poll_id, []))
        for websocket in websockets:
            try:
                await websocket.send_json(payload)
            except Exception:
                self.disconnect(poll_id, websocket)
