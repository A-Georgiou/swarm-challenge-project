"""Shared test fixtures: in-memory DB, TestClient, users, tokens, helpers."""

import os
from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import Base, get_db
from app.auth.auth import create_access_token, get_password_hash
from app.models.user import User
from app.models.project import Project
from app.models.task import Task

TEST_USER_PASSWORD = os.environ.get("TEST_USER_PASSWORD", "TestPass1")

# ---------------------------------------------------------------------------
# Test database (shared in-memory SQLite with StaticPool)
# ---------------------------------------------------------------------------
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Core fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def setup_database():
    """Create all tables before each test and drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    """Provide a test database session."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client():
    """FastAPI TestClient with the test database override."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# User fixtures
# ---------------------------------------------------------------------------
def _make_user(db, username, email, role):
    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(TEST_USER_PASSWORD),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_token(user_id: int) -> str:
    return create_access_token(data={"sub": str(user_id)})


@pytest.fixture()
def admin_user(db):
    return _make_user(db, "admin", "admin@test.com", "admin")


@pytest.fixture()
def editor_user(db):
    return _make_user(db, "editor", "editor@test.com", "editor")


@pytest.fixture()
def viewer_user(db):
    return _make_user(db, "viewer", "viewer@test.com", "viewer")


@pytest.fixture()
def admin_token(admin_user):
    return _make_token(admin_user.id)


@pytest.fixture()
def editor_token(editor_user):
    return _make_token(editor_user.id)


@pytest.fixture()
def viewer_token(viewer_user):
    return _make_token(viewer_user.id)


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Project / Task helpers
# ---------------------------------------------------------------------------
@pytest.fixture()
def test_project(db, editor_user):
    """Create a project owned by the editor user."""
    project = Project(
        name="Test Project",
        description="A project for testing",
        created_by=editor_user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@pytest.fixture()
def test_task(db, test_project, editor_user):
    """Create a task inside the test project."""
    task = Task(
        title="Test Task",
        description="A task for testing",
        status="todo",
        priority="medium",
        project_id=test_project.id,
        assignee_id=editor_user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def make_expired_token(user_id: int) -> str:
    """Create a JWT that is already expired."""
    return create_access_token(
        data={"sub": str(user_id)},
        expires_delta=timedelta(seconds=-1),
    )
