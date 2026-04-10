"""Comment schemas for request/response validation."""

from datetime import datetime

from pydantic import BaseModel, Field


# --- Create ---
class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1)
    task_id: int


# --- Update ---
class CommentUpdate(BaseModel):
    content: str | None = None


# --- Response ---
class CommentResponse(BaseModel):
    id: int
    content: str
    user_id: int
    task_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
