"""Load test: 50 concurrent WebSocket connections with broadcast verification."""

import asyncio
import time

import pytest
from unittest.mock import AsyncMock

from app.websocket import ConnectionManager


@pytest.mark.asyncio
async def test_50_concurrent_ws_broadcast():
    """Create 50 concurrent WebSocket connections to same project,
    broadcast a message, and verify all 50 receive it within reasonable time.
    """
    manager = ConnectionManager()
    project_id = 1
    num_clients = 50

    # Create 50 mock WebSocket objects
    mock_websockets = []
    for i in range(num_clients):
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        mock_websockets.append(ws)
        # Directly add to manager's active connections
        if project_id not in manager.active_connections:
            manager.active_connections[project_id] = []
        manager.active_connections[project_id].append((ws, i))

    assert len(manager.active_connections[project_id]) == num_clients

    # Broadcast a message and measure time
    message = {
        "type": "task_created",
        "data": {"id": 1, "title": "Load Test Task", "status": "todo"},
    }

    start = time.time()
    await manager.broadcast(project_id, message)
    elapsed = time.time() - start

    # Verify all 50 clients received the message
    for i, ws in enumerate(mock_websockets):
        ws.send_json.assert_called_once_with(message)

    # Should complete within a reasonable time (< 2 seconds for 50 clients)
    assert elapsed < 2.0, f"Broadcast to {num_clients} clients took {elapsed:.3f}s"


@pytest.mark.asyncio
async def test_50_concurrent_ws_connect_and_broadcast():
    """Use asyncio.gather to concurrently connect 50 clients and verify broadcast."""
    manager = ConnectionManager()
    project_id = 42
    num_clients = 50

    mock_websockets = []

    async def connect_client(client_id: int):
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        mock_websockets.append(ws)
        await manager.connect(ws, project_id, client_id)

    # Concurrently connect all 50 clients using asyncio.gather
    start = time.time()
    await asyncio.gather(*(connect_client(i) for i in range(num_clients)))
    connect_elapsed = time.time() - start

    assert len(manager.active_connections[project_id]) == num_clients
    assert connect_elapsed < 2.0, f"Connecting {num_clients} clients took {connect_elapsed:.3f}s"

    # Now broadcast and verify
    message = {"type": "task_updated", "data": {"id": 99, "status": "done"}}

    start = time.time()
    await manager.broadcast(project_id, message)
    broadcast_elapsed = time.time() - start

    for ws in mock_websockets:
        ws.send_json.assert_called_once_with(message)

    assert broadcast_elapsed < 2.0, f"Broadcast took {broadcast_elapsed:.3f}s"


@pytest.mark.asyncio
async def test_broadcast_handles_disconnected_clients():
    """Verify that broadcast gracefully handles clients that disconnect mid-broadcast."""
    manager = ConnectionManager()
    project_id = 7
    num_good = 45
    num_bad = 5

    all_ws = []

    # Good clients
    for i in range(num_good):
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        all_ws.append(ws)
        if project_id not in manager.active_connections:
            manager.active_connections[project_id] = []
        manager.active_connections[project_id].append((ws, i))

    # Bad clients that raise on send
    for i in range(num_bad):
        ws = AsyncMock()
        ws.send_json = AsyncMock(side_effect=Exception("Connection closed"))
        all_ws.append(ws)
        manager.active_connections[project_id].append((ws, num_good + i))

    message = {"type": "task_deleted", "data": {"id": 5}}
    await manager.broadcast(project_id, message)

    # Good clients received the message
    for ws in all_ws[:num_good]:
        ws.send_json.assert_called_once_with(message)

    # Bad clients were cleaned up
    remaining = len(manager.active_connections.get(project_id, []))
    assert remaining == num_good
