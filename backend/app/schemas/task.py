from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    priority: Optional[str] = "medium"
    task_type: Optional[str] = None
    estimated_hours: Optional[int] = None
    is_optional: Optional[bool] = False
    conditions: Optional[str] = None


class TaskCreate(TaskBase):
    event_id: Optional[int] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    completed: Optional[bool] = None
    priority: Optional[str] = None
    task_type: Optional[str] = None
    estimated_hours: Optional[int] = None
    is_optional: Optional[bool] = None
    conditions: Optional[str] = None


class TaskResponse(TaskBase):
    id: int
    user_id: int
    event_id: Optional[int] = None
    completed: bool
    prep_material: Optional[str] = None
    source_type: Optional[str] = None
    is_optional: bool
    conditions: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
