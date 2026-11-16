from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session
from .database import get_db
from .models import User, Member, Project
from .security import decode_token

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    uid = decode_token(token)
    user = db.get(User, uid) if uid else None
    if not user:
        raise HTTPException(401, "Недействительный токен")
    return user


def get_membership(db: Session, project_id: int, user_id: int) -> Member:
    m = db.scalar(select(Member).where(Member.project_id == project_id, Member.user_id == user_id))
    if not m:
        raise HTTPException(404, "Проект не найден")
    return m


def project_access(project_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Project:
    get_membership(db, project_id, user.id)
    return db.get(Project, project_id)
