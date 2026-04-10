import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.auth.auth import decode_access_token

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections grouped by project rooms."""

    def __init__(self):
        # Dict mapping project_id to set of (websocket, user_id) tuples
        self.active_connections: dict[int, list[tuple[WebSocket, int]]] = {}

    async def connect(self, websocket: WebSocket, project_id: int, user_id: int):
        """Accept a WebSocket and add it to a project room."""
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id].append((websocket, user_id))
        logger.info(f"User {user_id} connected to project {project_id}")

    def disconnect(self, websocket: WebSocket, project_id: int):
        """Remove a WebSocket from a project room."""
        if project_id in self.active_connections:
            self.active_connections[project_id] = [
                (ws, uid) for ws, uid in self.active_connections[project_id]
                if ws != websocket
            ]
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]

    async def broadcast(self, project_id: int, message: dict):
        """Send a JSON message to all clients connected to a project."""
        if project_id not in self.active_connections:
            return
        disconnected = []
        for websocket, user_id in self.active_connections[project_id]:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append((websocket, user_id))
        # Clean up broken connections
        for ws, uid in disconnected:
            self.disconnect(ws, project_id)


manager = ConnectionManager()

router = APIRouter()


@router.websocket("/ws/{project_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    project_id: int,
    token: str = Query(...),
):
    """WebSocket endpoint for real-time project updates.

    Authenticates via JWT token in query parameter.
    Joins the project room and broadcasts events.
    """
    # Authenticate via JWT
    payload = decode_access_token(token)
    if payload is None:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    user_id = payload.get("sub")
    if user_id is None:
        await websocket.close(code=4001, reason="Invalid token payload")
        return

    user_id = int(user_id)

    # Connect and join project room
    await manager.connect(websocket, project_id, user_id)

    # Broadcast user joined
    await manager.broadcast(project_id, {
        "type": "user_joined",
        "data": {"user_id": user_id, "project_id": project_id}
    })

    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                continue

            # Handle ping/pong keepalive
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)
        # Broadcast user left
        await manager.broadcast(project_id, {
            "type": "user_left",
            "data": {"user_id": user_id, "project_id": project_id}
        })
        logger.info(f"User {user_id} disconnected from project {project_id}")


async def notify_clients(project_id: int, event_type: str, data: dict) -> None:
    """Broadcast an event to all WebSocket clients in a project room.

    Called from CRUD routers via BackgroundTasks after mutations.

    Args:
        project_id: The project whose clients should be notified.
        event_type: Event name (e.g., 'task_created', 'task_updated', 'task_deleted',
                    'subtask_created', 'subtask_updated', 'subtask_deleted',
                    'comment_added', 'comment_updated', 'comment_deleted').
        data: The event payload (typically the serialized resource).
    """
    await manager.broadcast(project_id, {
        "type": event_type,
        "data": data,
    })
