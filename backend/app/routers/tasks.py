"""Tasks API router."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.task import Task
from app.schemas.common import APIResponse
from app.schemas.task import TaskCreate, TaskResponse

router = APIRouter()


@router.get("/", response_model=APIResponse)
async def list_tasks(db: Session = Depends(get_db)):
    """List all tasks."""
    tasks = db.query(Task).all()
    return APIResponse(
        data=[TaskResponse.model_validate(t) for t in tasks],
        timestamp=datetime.now(timezone.utc),
    )


@router.post("/", response_model=APIResponse, status_code=201)
async def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """Create a new task."""
    db_task = Task(**task.model_dump(), id=str(uuid.uuid4()))
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return APIResponse(
        data=TaskResponse.model_validate(db_task),
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/{task_id}", response_model=APIResponse)
async def get_task(task_id: str, db: Session = Depends(get_db)):
    """Get a task by ID."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return APIResponse(
        data=TaskResponse.model_validate(task),
        timestamp=datetime.now(timezone.utc),
    )
