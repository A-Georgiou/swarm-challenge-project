"""Task CRUD router."""

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_any_role, require_editor_or_admin
from app.db.database import get_db
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskPriority, TaskResponse, TaskStatus, TaskUpdate
from app.websocket import notify_clients

router = APIRouter(tags=["tasks"])


@router.post(
    "/api/projects/{project_id}/tasks",
    response_model=TaskResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def create_task(
    project_id: int,
    task_in: TaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor_or_admin),
):
    """Create a task in a project. Requires editor or admin role."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Project not found")

    task = Task(
        title=task_in.title,
        description=task_in.description,
        status=task_in.status.value,
        priority=task_in.priority.value,
        assignee_id=task_in.assignee_id,
        project_id=project_id,
        due_date=task_in.due_date,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    background_tasks.add_task(
        notify_clients, project_id, "task_created",
        {"id": task.id, "title": task.title, "status": task.status, "priority": task.priority,
         "assignee_id": task.assignee_id, "project_id": task.project_id},
    )
    return task


@router.get("/api/projects/{project_id}/tasks", response_model=list[TaskResponse])
def list_tasks(
    project_id: int,
    status: TaskStatus | None = Query(default=None),
    priority: TaskPriority | None = Query(default=None),
    assignee_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role),
):
    """List tasks for a project with optional filters. Requires viewer+ role."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Project not found")

    query = db.query(Task).filter(Task.project_id == project_id)
    if status is not None:
        query = query.filter(Task.status == status.value)
    if priority is not None:
        query = query.filter(Task.priority == priority.value)
    if assignee_id is not None:
        query = query.filter(Task.assignee_id == assignee_id)

    return query.all()


@router.get("/api/tasks/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role),
):
    """Get a task by ID with subtasks and comments. Requires viewer+ role."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.put("/api/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_in: TaskUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor_or_admin),
):
    """Update a task. Requires editor or admin role."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Task not found")

    update_data = task_in.model_dump(exclude_unset=True)
    # Convert enum values to their string representations for DB storage
    if "status" in update_data and update_data["status"] is not None:
        update_data["status"] = update_data["status"].value
    if "priority" in update_data and update_data["priority"] is not None:
        update_data["priority"] = update_data["priority"].value

    for field, value in update_data.items():
        setattr(task, field, value)

    # Manually update updated_at since setattr may not trigger onupdate
    task.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(task)
    background_tasks.add_task(
        notify_clients, task.project_id, "task_updated",
        {"id": task.id, "title": task.title, "status": task.status, "priority": task.priority,
         "assignee_id": task.assignee_id, "project_id": task.project_id},
    )
    return task


@router.delete("/api/tasks/{task_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor_or_admin),
):
    """Delete a task. Requires editor or admin role."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Task not found")

    task_data = {"id": task.id, "project_id": task.project_id}
    project_id = task.project_id
    db.delete(task)
    db.commit()
    background_tasks.add_task(notify_clients, project_id, "task_deleted", task_data)
