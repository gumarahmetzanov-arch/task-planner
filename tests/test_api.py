import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

import pytest
from fastapi.testclient import TestClient
from app.database import Base, engine
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


def signup(c, name):
    c.post("/api/auth/register", json={"username": name, "email": f"{name}@mail.ru", "password": "secret1"})
    t = c.post("/api/auth/login", data={"username": name, "password": "secret1"}).json()["access_token"]
    return {"Authorization": f"Bearer {t}"}


def test_full_flow(client):
    a, b, x = signup(client, "anna"), signup(client, "boris"), signup(client, "outsider")
    p = client.post("/api/projects", json={"name": "Диплом"}, headers=a).json()
    pid = p["id"]

    assert client.get(f"/api/projects/{pid}", headers=x).status_code == 404
    assert client.post(f"/api/projects/{pid}/members", json={"email": "boris@mail.ru"}, headers=a).status_code == 201
    assert client.post(f"/api/projects/{pid}/members", json={"email": "boris@mail.ru"}, headers=a).status_code == 409
    assert client.post(f"/api/projects/{pid}/members", json={"email": "x@mail.ru"}, headers=b).status_code == 403

    boris_id = client.get("/api/auth/me", headers=b).json()["id"]
    t = client.post(f"/api/projects/{pid}/tasks", headers=a,
                    json={"title": "Написать код", "priority": "high", "assignee_id": boris_id, "due_date": "2026-12-01"})
    assert t.status_code == 201
    tid = t.json()["id"]

    r = client.patch(f"/api/tasks/{tid}", json={"status": "in_progress"}, headers=b)
    assert r.json()["status"] == "in_progress"
    assert client.post(f"/api/tasks/{tid}/comments", json={"text": "Начал"}, headers=b).status_code == 201
    assert len(client.get(f"/api/tasks/{tid}", headers=a).json()["comments"]) == 1

    assert len(client.get(f"/api/projects/{pid}/tasks?status=done", headers=a).json()) == 0
    assert len(client.get(f"/api/projects/{pid}/tasks?assignee_id={boris_id}", headers=a).json()) == 1
    assert client.patch(f"/api/tasks/{tid}", json={"status": "x"}, headers=a).status_code == 422
    assert client.get(f"/api/tasks/{tid}", headers=x).status_code == 404

    outsider_id = client.get("/api/auth/me", headers=x).json()["id"]
    assert client.patch(f"/api/tasks/{tid}", json={"assignee_id": outsider_id}, headers=a).status_code == 404

    assert client.delete(f"/api/tasks/{tid}", headers=b).status_code == 204
    assert client.delete(f"/api/projects/{pid}", headers=b).status_code == 403
    assert client.delete(f"/api/projects/{pid}", headers=a).status_code == 204


def test_auth_errors(client):
    signup(client, "anna")
    assert client.post("/api/auth/register", json={"username": "anna", "email": "n@mail.ru", "password": "secret1"}).status_code == 409
    assert client.post("/api/auth/login", data={"username": "anna", "password": "bad"}).status_code == 401
    assert client.get("/api/projects").status_code == 401


def test_websocket_events(client):
    h = signup(client, "anna")
    pid = client.post("/api/projects", json={"name": "P"}, headers=h).json()["id"]
    token = h["Authorization"].split()[1]
    with client.websocket_connect(f"/ws/projects/{pid}?token={token}") as ws:
        client.post(f"/api/projects/{pid}/tasks", json={"title": "T"}, headers=h)
        assert ws.receive_json()["event"] == "task_created"
