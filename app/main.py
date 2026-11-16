from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .database import Base, engine, SessionLocal
from .deps import get_membership
from .realtime import manager
from .routers import auth, projects, tasks
from .security import decode_token
from fastapi import HTTPException

STATIC = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Сервис совместного планирования задач", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(tasks.router)


@app.websocket("/ws/projects/{project_id}")
async def project_ws(ws: WebSocket, project_id: int, token: str = ""):
    uid = decode_token(token)
    ok = False
    if uid:
        with SessionLocal() as db:
            try:
                get_membership(db, project_id, uid)
                ok = True
            except HTTPException:
                pass
    if not ok:
        await ws.close(code=4401)
        return
    await manager.connect(project_id, ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(project_id, ws)


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")
