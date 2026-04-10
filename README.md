# TaskBoard — Collaborative Task Manager

A real-time collaborative task management application built with **FastAPI**, **SQLite**, and a vanilla **HTML/JS/CSS** frontend. Features JWT authentication, role-based access control (RBAC), WebSocket-powered live updates, and a full REST API with auto-generated OpenAPI documentation.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Setup Instructions](#setup-instructions)
- [Default Admin Credentials](#default-admin-credentials)
- [API Documentation](#api-documentation)
- [API Endpoints Reference](#api-endpoints-reference)
- [Architecture Diagram](#architecture-diagram)
- [WebSocket Protocol](#websocket-protocol)
- [Testing](#testing)
- [Project Structure](#project-structure)

---

## Features

- **Project Management** — Create, update, and delete projects
- **Task Tracking** — Tasks with status (todo, in-progress, review, done) and priority (low, medium, high, urgent)
- **Subtasks** — Break tasks into smaller checklist items
- **Comments** — Threaded comments on tasks
- **Real-time Updates** — WebSocket-based live notifications per project room
- **JWT Authentication** — Secure token-based auth with 60-minute expiry
- **Role-Based Access Control** — Three roles: `admin`, `editor`, `viewer`
- **Auto-generated API Docs** — Swagger UI and ReDoc built in

## Tech Stack

| Layer      | Technology                        |
| ---------- | --------------------------------- |
| Backend    | Python 3.10+, FastAPI, Uvicorn    |
| Database   | SQLite (via SQLAlchemy ORM)       |
| Auth       | JWT (python-jose), bcrypt         |
| Real-time  | WebSockets (native FastAPI)       |
| Frontend   | Vanilla HTML, JavaScript, CSS     |
| Testing    | pytest, httpx, pytest-asyncio     |

---

## Setup Instructions

### Prerequisites

- **Python 3.10+**
- **pip** (Python package manager)

### Install & Run

```bash
# 1. Clone the repository
git clone <repo-url> && cd challenge-project

# 2. Install backend dependencies
cd backend
pip install -r requirements.txt

# 3. Start the application
uvicorn app.main:app --reload
```

### Access the Application

| URL                         | Description              |
| --------------------------- | ------------------------ |
| http://localhost:8000       | Frontend UI              |
| http://localhost:8000/docs  | Swagger UI (OpenAPI)     |
| http://localhost:8000/redoc | ReDoc API documentation  |

The SQLite database (`taskboard.db`) is created automatically on first startup. Tables are auto-migrated and a default admin user is seeded.

---

## Default Admin Credentials

| Field    | Value                   |
| -------- | ----------------------- |
| Username | `admin`                 |
| Password | `admin123`              |
| Email    | `admin@taskboard.local` |
| Role     | `admin`                 |

> ⚠️ **Change the default password in production.** The secret key in `app/auth/auth.py` should also be replaced with a secure, randomly generated value.

---

## API Documentation

FastAPI auto-generates interactive API documentation from the codebase:

- **Swagger UI** — [http://localhost:8000/docs](http://localhost:8000/docs) — Interactive API explorer with "Try it out" functionality
- **ReDoc** — [http://localhost:8000/redoc](http://localhost:8000/redoc) — Clean, readable API reference
- **OpenAPI JSON** — [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json) — Raw OpenAPI 3.x specification

All endpoints, schemas, and authentication requirements are documented automatically.

---

## API Endpoints Reference

### Authentication

All protected endpoints require a `Bearer` token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

#### Register

```
POST /api/auth/register
```

**Auth:** None

**Request Body:**

```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "secret123",
  "role": "editor"
}
```

**Response (201):**

```json
{
  "id": 2,
  "username": "johndoe",
  "email": "john@example.com",
  "role": "editor"
}
```

#### Login

```
POST /api/auth/login
```

**Auth:** None

**Request Body:**

```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response (200):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

#### Get Current User

```
GET /api/auth/me
```

**Auth:** Any authenticated user

**Response (200):**

```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@taskboard.local",
  "role": "admin"
}
```

---

### Users

| Method   | Path                 | Auth Required       | Description        |
| -------- | -------------------- | ------------------- | ------------------ |
| `GET`    | `/api/users/`        | Any authenticated   | List all users     |
| `GET`    | `/api/users/{id}`    | Any authenticated   | Get user by ID     |
| `PUT`    | `/api/users/{id}`    | Admin only          | Update a user      |
| `DELETE` | `/api/users/{id}`    | Admin only          | Delete a user      |

---

### Projects

| Method   | Path                      | Auth Required        | Description           |
| -------- | ------------------------- | -------------------- | --------------------- |
| `POST`   | `/api/projects/`          | Editor or Admin      | Create a project      |
| `GET`    | `/api/projects/`          | Any authenticated    | List all projects     |
| `GET`    | `/api/projects/{id}`      | Any authenticated    | Get project by ID     |
| `PUT`    | `/api/projects/{id}`      | Creator or Admin     | Update a project      |
| `DELETE` | `/api/projects/{id}`      | Creator or Admin     | Delete a project      |

**Create Project — Request Body:**

```json
{
  "name": "My Project",
  "description": "Project description"
}
```

**Project Response:**

```json
{
  "id": 1,
  "name": "My Project",
  "description": "Project description",
  "created_by": 1,
  "created_at": "2026-04-10T20:00:00Z"
}
```

---

### Tasks

| Method   | Path                                    | Auth Required    | Description                |
| -------- | --------------------------------------- | ---------------- | -------------------------- |
| `POST`   | `/api/projects/{project_id}/tasks`      | Editor or Admin  | Create a task in project   |
| `GET`    | `/api/projects/{project_id}/tasks`      | Any role         | List tasks (with filters)  |
| `GET`    | `/api/tasks/{id}`                       | Any role         | Get task by ID             |
| `PUT`    | `/api/tasks/{id}`                       | Editor or Admin  | Update a task              |
| `DELETE` | `/api/tasks/{id}`                       | Editor or Admin  | Delete a task              |

**Query Filters** (on `GET /api/projects/{project_id}/tasks`):
- `status` — `todo`, `in-progress`, `review`, `done`
- `priority` — `low`, `medium`, `high`, `urgent`
- `assignee_id` — integer user ID

**Create Task — Request Body:**

```json
{
  "title": "Implement login",
  "description": "Add JWT-based login",
  "status": "todo",
  "priority": "high",
  "assignee_id": 2,
  "project_id": 1,
  "due_date": "2026-04-20T00:00:00Z"
}
```

**Task Response:**

```json
{
  "id": 1,
  "title": "Implement login",
  "description": "Add JWT-based login",
  "status": "todo",
  "priority": "high",
  "assignee_id": 2,
  "project_id": 1,
  "due_date": "2026-04-20T00:00:00Z",
  "created_at": "2026-04-10T20:00:00Z",
  "updated_at": "2026-04-10T20:00:00Z"
}
```

---

### Subtasks

| Method   | Path                                  | Auth Required    | Description              |
| -------- | ------------------------------------- | ---------------- | ------------------------ |
| `POST`   | `/api/tasks/{task_id}/subtasks`       | Editor or Admin  | Create a subtask         |
| `GET`    | `/api/tasks/{task_id}/subtasks`       | Any authenticated| List subtasks for task   |
| `PUT`    | `/api/subtasks/{id}`                  | Editor or Admin  | Update a subtask         |
| `DELETE` | `/api/subtasks/{id}`                  | Editor or Admin  | Delete a subtask         |

**Create Subtask — Request Body:**

```json
{
  "title": "Write unit tests",
  "completed": false,
  "task_id": 1
}
```

**Subtask Response:**

```json
{
  "id": 1,
  "title": "Write unit tests",
  "completed": false,
  "task_id": 1
}
```

---

### Comments

| Method   | Path                                  | Auth Required       | Description              |
| -------- | ------------------------------------- | ------------------- | ------------------------ |
| `POST`   | `/api/tasks/{task_id}/comments`       | Any authenticated   | Add a comment            |
| `GET`    | `/api/tasks/{task_id}/comments`       | Any authenticated   | List comments for task   |
| `PUT`    | `/api/comments/{id}`                  | Author only         | Update a comment         |
| `DELETE` | `/api/comments/{id}`                  | Author or Admin     | Delete a comment         |

**Create Comment — Request Body:**

```json
{
  "content": "Looking good! Ready for review.",
  "task_id": 1
}
```

**Comment Response:**

```json
{
  "id": 1,
  "content": "Looking good! Ready for review.",
  "user_id": 2,
  "task_id": 1,
  "created_at": "2026-04-10T20:30:00Z"
}
```

---

### Health Check

```
GET /api/health
```

**Auth:** None

**Response:**

```json
{ "status": "ok" }
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT BROWSER                           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │           Frontend (HTML / JavaScript / CSS)              │  │
│  │             index.html  ·  app.js  ·  styles.css          │  │
│  └──────────────┬────────────────────────────┬───────────────┘  │
│                 │ HTTP (REST)                 │ WebSocket        │
└─────────────────┼────────────────────────────┼──────────────────┘
                  │                            │
                  ▼                            ▼
┌─────────────────────────────┐  ┌────────────────────────────────┐
│      FastAPI REST API       │  │    WebSocket Server            │
│                             │  │                                │
│  /api/auth/*                │  │  /ws/{project_id}?token=JWT    │
│  /api/users/*               │  │                                │
│  /api/projects/*            │  │  ┌──────────────────────────┐  │
│  /api/tasks/*               │  │  │  Connection Manager      │  │
│  /api/subtasks/*            │  │  │                          │  │
│  /api/comments/*            │  │  │  • Per-project rooms     │  │
│  /api/health                │  │  │  • Broadcast to room     │  │
│                             │  │  │  • Auto-cleanup on DC    │  │
├─────────────────────────────┤  │  └──────────────────────────┘  │
│        Auth Layer           │  │                                │
│  ┌───────────────────────┐  │  │  Events broadcast by REST     │
│  │  JWT (HS256, 60 min)  │  │  │  routers via BackgroundTasks  │
│  └───────────────────────┘  │  └───────────────┬────────────────┘
│  ┌───────────────────────┐  │                  │
│  │  RBAC Middleware       │  │                  │
│  │  admin > editor > viewer │                  │
│  └───────────────────────┘  │                  │
└──────────────┬──────────────┘                  │
               │                                 │
               ▼                                 │
┌─────────────────────────────────────────────────────────────────┐
│                    SQLAlchemy ORM Layer                          │
├─────────────────────────────────────────────────────────────────┤
│                     SQLite Database                              │
│                     (taskboard.db)                               │
│                                                                 │
│  Tables: users · projects · tasks · subtasks · comments         │
└─────────────────────────────────────────────────────────────────┘
```

### Auth Flow

```
Client                          Server
  │                               │
  │  POST /api/auth/login         │
  │  { username, password }       │
  │──────────────────────────────►│
  │                               │  Verify password (bcrypt)
  │                               │  Generate JWT (HS256)
  │  { access_token, token_type } │
  │◄──────────────────────────────│
  │                               │
  │  GET /api/tasks/1             │
  │  Authorization: Bearer <JWT>  │
  │──────────────────────────────►│
  │                               │  Decode JWT → extract user_id
  │                               │  Check role against endpoint RBAC
  │  200 OK / 403 Forbidden       │
  │◄──────────────────────────────│
```

### RBAC Roles

| Role     | Permissions                                              |
| -------- | -------------------------------------------------------- |
| `admin`  | Full access — CRUD all resources, manage users           |
| `editor` | Create/update/delete projects, tasks, subtasks; comment  |
| `viewer` | Read-only access to projects and tasks; can comment      |

---

## WebSocket Protocol

### Connection

```
ws://localhost:8000/ws/{project_id}?token=<JWT_ACCESS_TOKEN>
```

Authentication is performed via the `token` query parameter. An invalid or expired token results in an immediate close with code `4001`.

### Message Format

All messages are JSON objects with a `type` field and an optional `data` payload:

```json
{
  "type": "<event_type>",
  "data": { ... }
}
```

### Server → Client Events

| Event Type         | Trigger                        | Data Payload                                    |
| ------------------ | ------------------------------ | ----------------------------------------------- |
| `user_joined`      | Client connects to room        | `{ "user_id": 1, "project_id": 1 }`            |
| `user_left`        | Client disconnects from room   | `{ "user_id": 1, "project_id": 1 }`            |
| `task_created`     | New task created in project    | `{ "id", "title", "status", "priority", ... }`  |
| `task_updated`     | Task updated                   | `{ "id", "title", "status", "priority", ... }`  |
| `task_deleted`     | Task deleted                   | `{ "id", "project_id" }`                        |
| `subtask_created`  | Subtask added to a task        | `{ "id", "title", "completed", "task_id" }`     |
| `subtask_updated`  | Subtask updated                | `{ "id", "title", "completed", "task_id" }`     |
| `subtask_deleted`  | Subtask deleted                | `{ "id", "task_id" }`                           |
| `comment_added`    | Comment posted on a task       | `{ "id", "content", "user_id", "task_id" }`     |
| `comment_updated`  | Comment edited                 | `{ "id", "content", "user_id", "task_id" }`     |
| `comment_deleted`  | Comment removed                | `{ "id", "task_id" }`                           |

### Client → Server Events

| Event Type | Description           | Response        |
| ---------- | --------------------- | --------------- |
| `ping`     | Keepalive heartbeat   | `{ "type": "pong" }` |

### Connection Lifecycle

```
Client                              Server
  │  ws://…/ws/1?token=<JWT>          │
  │──────────────────────────────────►│  Validate JWT
  │                                   │  Accept connection
  │  ◄── { type: "user_joined" } ──  │  Broadcast to room
  │                                   │
  │  ── { type: "ping" } ──────────► │
  │  ◄── { type: "pong" } ────────── │
  │                                   │
  │        … live events …            │
  │                                   │
  │  [disconnect]                     │
  │──────────────────────────────────►│
  │                                   │  Broadcast "user_left"
  │                                   │  Clean up connection
```

---

## Testing

### Running Tests

```bash
cd backend
pytest -v
```

### Test Coverage

| Test File              | Coverage Area                                       |
| ---------------------- | --------------------------------------------------- |
| `test_auth.py`         | Registration, login, JWT validation, `/me` endpoint |
| `test_users.py`        | User CRUD, admin-only enforcement                   |
| `test_projects.py`     | Project CRUD, ownership checks                      |
| `test_tasks.py`        | Task CRUD, filters, RBAC enforcement                |
| `test_subtasks.py`     | Subtask CRUD, completion toggling                   |
| `test_comments.py`     | Comment CRUD, author-only update/delete             |
| `test_websocket.py`    | WebSocket connection, auth, messaging               |
| `test_load.py`         | Load testing (50 concurrent WebSocket connections)  |

### Load Tests

The `test_load.py` module validates WebSocket performance:

- **50 concurrent connections** — Verifies all clients connect and receive broadcasts within 2 seconds
- **Concurrent connect + broadcast** — Uses `asyncio.gather` to simulate simultaneous joins
- **Disconnection resilience** — Ensures broken connections (5 out of 50) are cleaned up gracefully without affecting healthy clients

---

## Project Structure

```
challenge-project/
├── README.md                          # This file
├── frontend/
│   ├── index.html                     # Main HTML page (SPA shell)
│   ├── app.js                         # Frontend application logic
│   └── styles.css                     # Stylesheet
└── backend/
    ├── requirements.txt               # Python dependencies
    ├── taskboard.db                   # SQLite database (auto-created)
    ├── app/
    │   ├── __init__.py
    │   ├── main.py                    # FastAPI app entry point, lifespan, router registration
    │   ├── websocket.py               # WebSocket endpoint, ConnectionManager, notify_clients()
    │   ├── auth/
    │   │   ├── __init__.py
    │   │   ├── auth.py                # JWT creation/verification, password hashing (bcrypt)
    │   │   └── dependencies.py        # FastAPI deps: get_current_user, RBAC (require_admin, etc.)
    │   ├── db/
    │   │   ├── __init__.py
    │   │   ├── database.py            # SQLAlchemy engine, session factory, Base class
    │   │   ├── init_db.py             # Database initialization utilities
    │   │   └── seed.py                # Seeds default admin user on first startup
    │   ├── models/
    │   │   ├── __init__.py
    │   │   ├── user.py                # User model (id, username, email, role, hashed_password)
    │   │   ├── project.py             # Project model (id, name, description, created_by)
    │   │   ├── task.py                # Task model (status, priority, assignee, due_date, timestamps)
    │   │   ├── subtask.py             # Subtask model (title, completed, task_id)
    │   │   └── comment.py             # Comment model (content, user_id, task_id, created_at)
    │   ├── routers/
    │   │   ├── __init__.py
    │   │   ├── auth.py                # POST /register, /login; GET /me
    │   │   ├── users.py               # User CRUD (admin-only for writes)
    │   │   ├── projects.py            # Project CRUD (editor+ for creates)
    │   │   ├── tasks.py               # Task CRUD with filters, WebSocket notifications
    │   │   ├── subtasks.py            # Subtask CRUD with WebSocket notifications
    │   │   └── comments.py            # Comment CRUD with WebSocket notifications
    │   └── schemas/
    │       ├── __init__.py
    │       ├── auth.py                # Token, LoginRequest schemas
    │       ├── user.py                # UserCreate, UserUpdate, UserResponse
    │       ├── project.py             # ProjectCreate, ProjectUpdate, ProjectResponse
    │       ├── task.py                # TaskCreate, TaskUpdate, TaskResponse, enums
    │       ├── subtask.py             # SubtaskCreate, SubtaskUpdate, SubtaskResponse
    │       └── comment.py             # CommentCreate, CommentUpdate, CommentResponse
    └── tests/
        ├── __init__.py
        ├── conftest.py                # Shared fixtures: test DB, users, tokens, helpers
        ├── test_auth.py               # Authentication endpoint tests
        ├── test_users.py              # User management tests
        ├── test_projects.py           # Project CRUD tests
        ├── test_tasks.py              # Task CRUD + filter tests
        ├── test_subtasks.py           # Subtask CRUD tests
        ├── test_comments.py           # Comment CRUD tests
        ├── test_websocket.py          # WebSocket connection/auth tests
        └── test_load.py               # 50-client WebSocket load tests
```
