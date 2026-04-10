"""Project schemas for request/response validation."""

from datetime import datetime

from pydantic import BaseModel, Field


# --- Create ---
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="")


# --- Update ---
class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


# --- Response ---
class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str
    created_by: int
    created_at: datetime

    model_config = {"from_attributes": True}
