"""Subtask model."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.database import Base


class Subtask(Base):
    __tablename__ = "subtasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    completed = Column(Boolean, default=False, nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)

    # Relationships
    task = relationship("Task", back_populates="subtasks")
