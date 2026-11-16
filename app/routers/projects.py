from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..deps import current_user, project_access, get_membership
from ..models import User, Project, Member
from ..realtime import manager
from ..schemas import ProjectCreate, ProjectOut, MemberAdd

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(data: ProjectCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = Project(name=data.name, description=data.description, owner_id=user.id)
    p.members.append(Member(user_id=user.id, role="owner"))
    db.add(p)
    db.commit()
    return p


@router.get("", response_model=list[ProjectOut])
def list_projects(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(Project).join(Member).where(Member.user_id == user.id).order_by(Project.id)
    ).all()


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(p: Project = Depends(project_access)):
    return p


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = get_membership(db, project_id, user.id)
    if m.role != "owner":
        raise HTTPException(403, "Только владелец может удалить проект")
    db.delete(db.get(Project, project_id))
    db.commit()


@router.post("/{project_id}/members", response_model=ProjectOut, status_code=201)
async def add_member(project_id: int, data: MemberAdd, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = get_membership(db, project_id, user.id)
    if m.role != "owner":
        raise HTTPException(403, "Только владелец может добавлять участников")
    target = db.scalar(select(User).where(User.email == data.email))
    if not target:
        raise HTTPException(404, "Пользователь с таким email не найден")
    p = db.get(Project, project_id)
    if any(x.user_id == target.id for x in p.members):
        raise HTTPException(409, "Пользователь уже в проекте")
    p.members.append(Member(user_id=target.id, role="member"))
    db.commit()
    await manager.broadcast(project_id, "member_added", {"user_id": target.id})
    return p


@router.delete("/{project_id}/members/{user_id}", status_code=204)
async def remove_member(project_id: int, user_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = get_membership(db, project_id, user.id)
    if m.role != "owner" and user_id != user.id:
        raise HTTPException(403, "Недостаточно прав")
    target = get_membership(db, project_id, user_id)
    if target.role == "owner":
        raise HTTPException(400, "Владельца нельзя удалить из проекта")
    db.delete(target)
    db.commit()
    await manager.broadcast(project_id, "member_removed", {"user_id": user_id})
