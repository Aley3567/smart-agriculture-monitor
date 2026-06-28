import json
from fastapi import WebSocket


class WSManager:
    def __init__(self):
        self.bridge_ws: WebSocket | None = None
        self.data_clients: list[WebSocket] = []

    async def connect_bridge(self, ws: WebSocket):
        await ws.accept()
        self.bridge_ws = ws

    def disconnect_bridge(self):
        self.bridge_ws = None

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
        if self.bridge_ws:
            try:
                await self.bridge_ws.send_json(data)
            except Exception:
                self.bridge_ws = None


manager = WSManager()
