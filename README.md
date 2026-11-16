# Сервис для совместного планирования задач

Backend: FastAPI + SQLAlchemy (SQLite). Frontend: один HTML-файл (канбан-доска). Обновления у всех участников приходят по WebSocket.

## Запуск

    pip install -r requirements.txt
    uvicorn app.main:app --reload

Откройте http://127.0.0.1:8000 (интерфейс) или http://127.0.0.1:8000/docs (документация API).

## Тесты

    pytest

## Возможности

- Регистрация и вход (JWT)
- Проекты, участники (владелец добавляет по email)
- Задачи: статус, приоритет, срок, исполнитель, комментарии, фильтр по исполнителю
- Доступ к проекту только у его участников
- Обновление доски в реальном времени (WebSocket)

## Структура

    app/main.py        приложение и WebSocket
    app/models.py      модели БД
    app/schemas.py     схемы запросов и ответов
    app/routers/       auth, projects, tasks
    app/realtime.py    рассылка событий
    static/index.html  веб-интерфейс
    tests/             автотесты

Переменные окружения: DATABASE_URL (по умолчанию sqlite:///./planner.db), SECRET_KEY.
