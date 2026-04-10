"""Tests for WebSocket endpoint /ws/{project_id}."""

import pytest
from starlette.testclient import TestClient as _StarletteClient
from starlette.websockets import WebSocketDisconnect

from tests.conftest import auth_header


class TestWebSocketConnect:
    def test_ws_connect_valid_jwt(self, client, editor_token, test_project):
        """Valid JWT should open the connection and receive a user_joined message."""
        with client.websocket_connect(
            f"/ws/{test_project.id}?token={editor_token}"
        ) as ws:
            data = ws.receive_json()
            assert data["type"] == "user_joined"
            assert data["data"]["project_id"] == test_project.id

    def test_ws_reject_invalid_jwt(self, client, test_project):
        """Invalid JWT should cause the server to close the connection."""
        with pytest.raises(Exception):
            with client.websocket_connect(
                f"/ws/{test_project.id}?token=bad.token.value"
            ) as ws:
                ws.receive_json()

    def test_ws_ping_pong(self, client, editor_token, test_project):
        """Client sends a ping, server responds with pong."""
        with client.websocket_connect(
            f"/ws/{test_project.id}?token={editor_token}"
        ) as ws:
            ws.receive_json()  # user_joined
            ws.send_json({"type": "ping"})
            resp = ws.receive_json()
            assert resp["type"] == "pong"


class TestWebSocketBroadcast:
    def test_ws_broadcast_on_task_create(self, client, editor_token, test_project):
        """Creating a task should trigger a broadcast to WebSocket clients."""
        with client.websocket_connect(
            f"/ws/{test_project.id}?token={editor_token}"
        ) as ws:
            ws.receive_json()  # user_joined

            # Create a task via REST API (runs background task for WS broadcast)
            resp = client.post(
                f"/api/projects/{test_project.id}/tasks",
                json={"title": "WS Task", "project_id": test_project.id},
                headers=auth_header(editor_token),
            )
            assert resp.status_code == 201

            msg = ws.receive_json()
            assert msg["type"] == "task_created"
            assert msg["data"]["title"] == "WS Task"

    def test_ws_broadcast_on_task_update(self, client, editor_token, test_project, test_task):
        """Updating a task should broadcast to connected clients."""
        with client.websocket_connect(
            f"/ws/{test_project.id}?token={editor_token}"
        ) as ws:
            ws.receive_json()  # user_joined

            resp = client.put(
                f"/api/tasks/{test_task.id}",
                json={"status": "done"},
                headers=auth_header(editor_token),
            )
            assert resp.status_code == 200

            msg = ws.receive_json()
            assert msg["type"] == "task_updated"
            assert msg["data"]["status"] == "done"

    def test_ws_broadcast_on_task_delete(self, client, editor_token, test_project, test_task):
        """Deleting a task should broadcast to connected clients."""
        with client.websocket_connect(
            f"/ws/{test_project.id}?token={editor_token}"
        ) as ws:
            ws.receive_json()  # user_joined

            resp = client.delete(
                f"/api/tasks/{test_task.id}",
                headers=auth_header(editor_token),
            )
            assert resp.status_code == 204

            msg = ws.receive_json()
            assert msg["type"] == "task_deleted"
            assert msg["data"]["id"] == test_task.id

    def test_ws_multi_client_broadcast(
        self, client, editor_token, admin_token, test_project
    ):
        """Two clients in the same project room should both receive broadcasts."""
        with client.websocket_connect(
            f"/ws/{test_project.id}?token={editor_token}"
        ) as ws1:
            ws1.receive_json()  # user_joined for ws1

            with client.websocket_connect(
                f"/ws/{test_project.id}?token={admin_token}"
            ) as ws2:
                # ws1 receives user_joined for ws2
                ws1_msg = ws1.receive_json()
                assert ws1_msg["type"] == "user_joined"

                # ws2 receives its own user_joined
                ws2_msg = ws2.receive_json()
                assert ws2_msg["type"] == "user_joined"

                # Create a task — both should get the broadcast
                resp = client.post(
                    f"/api/projects/{test_project.id}/tasks",
                    json={"title": "Shared Task", "project_id": test_project.id},
                    headers=auth_header(editor_token),
                )
                assert resp.status_code == 201

                msg1 = ws1.receive_json()
                msg2 = ws2.receive_json()
                assert msg1["type"] == "task_created"
                assert msg2["type"] == "task_created"
                assert msg1["data"]["title"] == "Shared Task"
                assert msg2["data"]["title"] == "Shared Task"
