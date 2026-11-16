from collections import defaultdict
from fastapi import WebSocket


class Manager:
    """Рассылка событий всем участникам проекта, подключённым по WebSocket."""

    def __init__(self):
        self.rooms: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect(self, project_id: int, ws: WebSocket):
        await ws.accept()
        self.rooms[project_id].add(ws)

    def disconnect(self, project_id: int, ws: WebSocket):
        self.rooms[project_id].discard(ws)

    async def broadcast(self, project_id: int, event: str, data: dict | None = None):
        for ws in list(self.rooms[project_id]):
            try:
                await ws.send_json({"event": event, "data": data or {}})
            except Exception:
                self.disconnect(project_id, ws)


manager = Manager()
