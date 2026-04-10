"""Comment CRUD router."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.models.comment import Comment
from app.models.task import Task
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentResponse, CommentUpdate
from app.websocket import notify_clients

router = APIRouter(tags=["comments"])


@router.post(
    "/api/tasks/{task_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    task_id: int,
    comment_in: CommentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a comment on a task. Any authenticated user can comment."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    comment = Comment(
        content=comment_in.content,
        user_id=current_user.id,
        task_id=task_id,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    background_tasks.add_task(
        notify_clients, task.project_id, "comment_added",
        {"id": comment.id, "content": comment.content, "user_id": comment.user_id, "task_id": task_id},
    )
    return comment


@router.get("/api/tasks/{task_id}/comments", response_model=list[CommentResponse])
def list_comments(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List comments for a task. Any authenticated user can view."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    return db.query(Comment).filter(Comment.task_id == task_id).all()


@router.put("/api/comments/{comment_id}", response_model=CommentResponse)
def update_comment(
    comment_id: int,
    comment_in: CommentUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a comment. Only the author can update."""
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    if comment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to update this comment")

    update_data = comment_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(comment, field, value)

    db.commit()
    db.refresh(comment)
    task = db.query(Task).filter(Task.id == comment.task_id).first()
    background_tasks.add_task(
        notify_clients, task.project_id, "comment_updated",
        {"id": comment.id, "content": comment.content, "user_id": comment.user_id, "task_id": comment.task_id},
    )
    return comment


@router.delete("/api/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    comment_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a comment. Only the author or an admin can delete."""
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    if comment.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to delete this comment")

    comment_data = {"id": comment.id, "task_id": comment.task_id}
    task = db.query(Task).filter(Task.id == comment.task_id).first()
    project_id = task.project_id
    db.delete(comment)
    db.commit()
    background_tasks.add_task(notify_clients, project_id, "comment_deleted", comment_data)
