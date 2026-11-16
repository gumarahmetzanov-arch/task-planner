from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

Status = Literal["todo", "in_progress", "done"]
Priority = Literal["low", "medium", "high"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=6, max_length=128)


class UserOut(ORM):
    id: int
    username: str
    email: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""


class MemberOut(ORM):
    role: str
    user: UserOut


class ProjectOut(ORM):
    id: int
    name: str
    description: str
    owner_id: int
    members: list[MemberOut] = []


class MemberAdd(BaseModel):
    email: str


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    status: Status = "todo"
    priority: Priority = "medium"
    due_date: date | None = None
    assignee_id: int | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: Status | None = None
    priority: Priority | None = None
    due_date: date | None = None
    assignee_id: int | None = None


class CommentCreate(BaseModel):
    text: str = Field(min_length=1)


class CommentOut(ORM):
    id: int
    author_id: int
    text: str
    created_at: datetime


class TaskOut(ORM):
    id: int
    project_id: int
    title: str
    description: str
    status: str
    priority: str
    due_date: date | None
    assignee_id: int | None
    creator_id: int
    created_at: datetime
    updated_at: datetime
    comments: list[CommentOut] = []
