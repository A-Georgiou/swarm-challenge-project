"""Database initialization script.

Run this to create all tables in the SQLite database.
Usage: python -m app.db.init_db
"""

import sys
import os

# Ensure the backend directory is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.database import Base, engine
from app.models import Comment, Project, Subtask, Task, User  # noqa: F401 - import to register models


def init_db():
    """Create all tables defined by the models."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")

    # Print table names for verification
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Tables: {', '.join(tables)}")


if __name__ == "__main__":
    init_db()
