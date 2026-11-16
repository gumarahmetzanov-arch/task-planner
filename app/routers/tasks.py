from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..deps import current_user, get_membership
from ..models import User, Task, Comment
from ..realtime import manager
from ..schemas import TaskCreate, TaskUpdate, TaskOut, CommentCreate, CommentOut

router = APIRouter(prefix="/api", tags=["tasks"])


def _check_assignee(db: Session, project_id: int, assignee_id: int | None):
    if assignee_id is not None:
        get_membership(db, project_id, assignee_id)


def _task(db: Session, task_id: int, user: User) -> Task:
    t = db.get(Task, task_id)
    if not t:
        raise HTTPException(404, "Задача не найдена")
    get_membership(db, t.project_id, user.id)
    return t


@router.post("/projects/{project_id}/tasks", response_model=TaskOut, status_code=201)
async def create_task(project_id: int, data: TaskCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    get_membership(db, project_id, user.id)
    _check_assignee(db, project_id, data.assignee_id)
    t = Task(**data.model_dump(), project_id=project_id, creator_id=user.id)
    db.add(t)
    db.commit()
    await manager.broadcast(project_id, "task_created", {"id": t.id})
    return t


@router.get("/projects/{project_id}/tasks", response_model=list[TaskOut])
def list_tasks(
    project_id: int,
    status: str | None = None,
    assignee_id: int | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    get_membership(db, project_id, user.id)
    q = select(Task).where(Task.project_id == project_id)
    if status:
        q = q.where(Task.status == status)
    if assignee_id is not None:
        q = q.where(Task.assignee_id == assignee_id)
    return db.scalars(q.order_by(Task.id)).all()


@router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _task(db, task_id, user)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
async def update_task(task_id: int, data: TaskUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    t = _task(db, task_id, user)
    changes = data.model_dump(exclude_unset=True)
    if "assignee_id" in changes:
        _check_assignee(db, t.project_id, changes["assignee_id"])
    for k, v in changes.items():
        setattr(t, k, v)
    db.commit()
    await manager.broadcast(t.project_id, "task_updated", {"id": t.id})
    return t


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    t = _task(db, task_id, user)
    pid = t.project_id
    db.delete(t)
    db.commit()
    await manager.broadcast(pid, "task_deleted", {"id": task_id})


@router.post("/tasks/{task_id}/comments", response_model=CommentOut, status_code=201)
async def add_comment(task_id: int, data: CommentCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    t = _task(db, task_id, user)
    c = Comment(task_id=t.id, author_id=user.id, text=data.text)
    db.add(c)
    db.commit()
    await manager.broadcast(t.project_id, "comment_added", {"task_id": t.id})
    return c
