"""User schemas for request/response validation."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# --- Create ---
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6)
    role: str = Field(default="member")


# --- Update ---
class UserUpdate(BaseModel):
    username: str | None = None
    email: str | None = None
    role: str | None = None


# --- Response ---
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str

    model_config = {"from_attributes": True}


class UserBrief(BaseModel):
    """Minimal user info for embedding in other responses."""
    id: int
    username: str

    model_config = {"from_attributes": True}
