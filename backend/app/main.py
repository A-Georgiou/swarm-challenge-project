"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.db.database import Base, SessionLocal, engine
from app.db.seed import seed_default_admin
from app.models import Comment, Project, Subtask, Task, User  # noqa: F401
from app.routers import auth, comments, projects, subtasks, tasks, users
from app.websocket import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: create tables and seed data on startup."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_default_admin(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="TaskBoard API",
    description="Collaborative task management API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(subtasks.router)
app.include_router(comments.router)
app.include_router(ws_router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


# Frontend static files
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


@app.get("/")
def serve_frontend():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
