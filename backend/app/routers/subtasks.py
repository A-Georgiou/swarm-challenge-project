"""Subtask CRUD router."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_editor_or_admin
from app.db.database import get_db
from app.models.subtask import Subtask
from app.models.task import Task
from app.models.user import User
from app.schemas.subtask import SubtaskCreate, SubtaskResponse, SubtaskUpdate
from app.websocket import notify_clients

router = APIRouter(tags=["subtasks"])


@router.post(
    "/api/tasks/{task_id}/subtasks",
    response_model=SubtaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_subtask(
    task_id: int,
    subtask_in: SubtaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor_or_admin),
):
    """Create a subtask for a task. Requires editor or admin role."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    subtask = Subtask(
        title=subtask_in.title,
        completed=subtask_in.completed,
        task_id=task_id,
    )
    db.add(subtask)
    db.commit()
    db.refresh(subtask)
    background_tasks.add_task(
        notify_clients, task.project_id, "subtask_created",
        {"id": subtask.id, "title": subtask.title, "completed": subtask.completed, "task_id": task_id},
    )
    return subtask


@router.get("/api/tasks/{task_id}/subtasks", response_model=list[SubtaskResponse])
def list_subtasks(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List subtasks for a task. Any authenticated user can view."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    return db.query(Subtask).filter(Subtask.task_id == task_id).all()


@router.put("/api/subtasks/{subtask_id}", response_model=SubtaskResponse)
def update_subtask(
    subtask_id: int,
    subtask_in: SubtaskUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor_or_admin),
):
    """Update a subtask (e.g. toggle complete). Requires editor or admin role."""
    subtask = db.query(Subtask).filter(Subtask.id == subtask_id).first()
    if not subtask:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subtask not found")

    update_data = subtask_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(subtask, field, value)

    db.commit()
    db.refresh(subtask)
    task = db.query(Task).filter(Task.id == subtask.task_id).first()
    background_tasks.add_task(
        notify_clients, task.project_id, "subtask_updated",
        {"id": subtask.id, "title": subtask.title, "completed": subtask.completed, "task_id": subtask.task_id},
    )
    return subtask


@router.delete("/api/subtasks/{subtask_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subtask(
    subtask_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor_or_admin),
):
    """Delete a subtask. Requires editor or admin role."""
    subtask = db.query(Subtask).filter(Subtask.id == subtask_id).first()
    if not subtask:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subtask not found")

    subtask_data = {"id": subtask.id, "task_id": subtask.task_id}
    task = db.query(Task).filter(Task.id == subtask.task_id).first()
    project_id = task.project_id
    db.delete(subtask)
    db.commit()
    background_tasks.add_task(notify_clients, project_id, "subtask_deleted", subtask_data)
