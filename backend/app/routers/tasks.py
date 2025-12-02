from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
from app.database import get_db
from app.models.user import User
from app.models.task import Task
from app.models.event import Event
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.utils.auth import get_current_user
from app.utils.llm_service import generate_prep_material
from app.services.scheduler import SchedulerService
import json

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    generate_prep: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new task."""
    # If no event_id provided and task has a deadline, create a calendar event
    event_id = task_data.event_id
    if not event_id and task_data.deadline:
        # Create calendar event for the task deadline
        event_start = task_data.deadline.replace(hour=23, minute=59, second=0, microsecond=0)
        event_end = event_start + timedelta(hours=1)
        
        new_event = Event(
            user_id=current_user.id,
            title=f"📅 {task_data.title}",
            description=task_data.description or "",
            start_time=event_start,
            end_time=event_end,
            event_type="deadline",
            source="manual"
        )
        db.add(new_event)
        db.flush()  # Get the event ID
        event_id = new_event.id
    
    new_task = Task(
        user_id=current_user.id,
        event_id=event_id,
        title=task_data.title,
        description=task_data.description,
        deadline=task_data.deadline,
        priority=task_data.priority,
        task_type=task_data.task_type,
        estimated_hours=task_data.estimated_hours,
        source_type="manual"
    )
    
    # Generate prep material if requested and task type is suitable
    if generate_prep and task_data.task_type in ["exam_prep", "interview_prep"]:
        prep_material = generate_prep_material(
            task_data.title,
            task_data.task_type,
            task_data.description or ""
        )
        new_task.prep_material = json.dumps(prep_material)
    
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    return new_task


@router.get("/", response_model=List[TaskResponse])
async def get_tasks(
    skip: int = 0,
    limit: int = 100,
    completed: bool = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all tasks for the current user."""
    query = db.query(Task).filter(Task.user_id == current_user.id)
    
    if completed is not None:
        query = query.filter(Task.completed == completed)
    
    tasks = query.offset(skip).limit(limit).all()
    
    return tasks


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific task."""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    return task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a task."""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Update fields
    update_data = task_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a task."""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    db.delete(task)
    db.commit()
    
    return None


@router.post("/{task_id}/schedule", response_model=dict)
async def schedule_prep_sessions(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Auto-schedule prep sessions for a task."""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    scheduler = SchedulerService(db, current_user.id)
    sessions = scheduler.auto_schedule_prep_sessions(task_id)
    
    return {
        "task_id": task_id,
        "suggested_sessions": sessions,
        "message": f"Found {len(sessions)} available time slots for prep sessions"
    }


@router.post("/{task_id}/regenerate-prep", response_model=TaskResponse)
async def regenerate_prep_material(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Regenerate prep material for a task."""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    if task.task_type not in ["exam_prep", "interview_prep"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prep material can only be generated for exam_prep or interview_prep tasks"
        )
    
    prep_material = generate_prep_material(
        task.title,
        task.task_type,
        task.description or ""
    )
    task.prep_material = json.dumps(prep_material)
    task.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(task)
    
    return task
