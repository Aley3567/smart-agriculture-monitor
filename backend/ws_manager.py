import json
from fastapi import WebSocket


class WSManager:
    def __init__(self):
        self.bridge_ws: WebSocket | None = None
        self.bridge_clients: dict[str, WebSocket] = {}
        self.data_clients: list[WebSocket] = []

    async def connect_bridge(self, ws: WebSocket, board_id: str = "A"):
        await ws.accept()
        self.register_bridge(board_id, ws)

    def register_bridge(self, board_id: str, ws: WebSocket):
        for existing_id, bridge in list(self.bridge_clients.items()):
            if bridge is ws and existing_id != board_id:
                del self.bridge_clients[existing_id]
        self.bridge_ws = ws
        self.bridge_clients[board_id] = ws

    def disconnect_bridge(self, ws: WebSocket | None = None):
        if ws is None or self.bridge_ws is ws:
            self.bridge_ws = None
        for board_id, bridge in list(self.bridge_clients.items()):
            if ws is None or bridge is ws:
                del self.bridge_clients[board_id]

    def has_bridge(self, board_id: str | None = None) -> bool:
        if board_id:
            return board_id in self.bridge_clients
        return self.bridge_ws is not None

    async def connect_client(self, ws: WebSocket):
        await ws.accept()
        self.data_clients.append(ws)

    def disconnect_client(self, ws: WebSocket):
        if ws in self.data_clients:
            self.data_clients.remove(ws)

    async def broadcast_to_clients(self, data: dict):
        dead = []
        for client in self.data_clients:
            try:
                await client.send_json(data)
            except Exception:
                dead.append(client)
        for client in dead:
            self.disconnect_client(client)

    async def send_to_bridge(self, data: dict):
        target = data.get("board_id")
        bridge = self.bridge_clients.get(target) if target else self.bridge_ws
        if bridge is None and not target:
            bridge = self.bridge_ws
        if bridge:
            try:
                await bridge.send_json(data)
            except Exception:
                self.disconnect_bridge(bridge)


manager = WSManager()
