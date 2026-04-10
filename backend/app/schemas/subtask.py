"""Subtask schemas for request/response validation."""

from pydantic import BaseModel, Field


# --- Create ---
class SubtaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    completed: bool = Field(default=False)
    task_id: int


# --- Update ---
class SubtaskUpdate(BaseModel):
    title: str | None = None
    completed: bool | None = None


# --- Response ---
class SubtaskResponse(BaseModel):
    id: int
    title: str
    completed: bool
    task_id: int

    model_config = {"from_attributes": True}
