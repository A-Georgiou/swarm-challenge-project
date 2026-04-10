"""Seed database with default data."""

import os

from sqlalchemy.orm import Session

from app.auth.auth import get_password_hash
from app.models.user import User

DEFAULT_ADMIN_USERNAME = os.environ.get("DEFAULT_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_EMAIL = os.environ.get("DEFAULT_ADMIN_EMAIL", "admin@taskboard.local")
DEFAULT_ADMIN_PASSWORD = os.environ.get("DEFAULT_ADMIN_PASSWORD", os.urandom(16).hex())


def seed_default_admin(db: Session) -> None:
    """Create a default admin user if one doesn't already exist."""
    existing = db.query(User).filter(User.role == "admin").first()
    if existing:
        return

    admin = User(
        username=DEFAULT_ADMIN_USERNAME,
        email=DEFAULT_ADMIN_EMAIL,
        hashed_password=get_password_hash(DEFAULT_ADMIN_PASSWORD),
        role="admin",
    )
    db.add(admin)
    db.commit()
    print(f"Default admin user created: {DEFAULT_ADMIN_USERNAME}")
