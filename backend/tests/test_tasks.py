"""Tests for task endpoints: create, list (with filters), get, update, delete, RBAC."""

import pytest
from tests.conftest import auth_header


class TestCreateTask:
    def test_create_task(self, client, editor_token, test_project):
        resp = client.post(
            f"/api/projects/{test_project.id}/tasks",
            json={
                "title": "New Task",
                "description": "A new task",
                "status": "todo",
                "priority": "high",
                "project_id": test_project.id,
            },
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "New Task"
        assert data["status"] == "todo"
        assert data["priority"] == "high"
        assert data["project_id"] == test_project.id

    def test_create_task_project_not_found(self, client, editor_token):
        resp = client.post(
            "/api/projects/9999/tasks",
            json={"title": "X", "project_id": 9999},
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 404


class TestListTasks:
    def test_list_tasks(self, client, editor_token, test_project, test_task):
        resp = client.get(
            f"/api/projects/{test_project.id}/tasks",
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert any(t["title"] == "Test Task" for t in data)

    def test_list_tasks_filter_status(self, client, editor_token, test_project, test_task):
        resp = client.get(
            f"/api/projects/{test_project.id}/tasks?status=todo",
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 200
        for t in resp.json():
            assert t["status"] == "todo"

    def test_list_tasks_filter_status_empty(self, client, editor_token, test_project, test_task):
        resp = client.get(
            f"/api/projects/{test_project.id}/tasks?status=done",
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_tasks_filter_priority(self, client, editor_token, test_project, test_task):
        resp = client.get(
            f"/api/projects/{test_project.id}/tasks?priority=medium",
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 200
        for t in resp.json():
            assert t["priority"] == "medium"

    def test_list_tasks_filter_assignee(self, client, editor_user, editor_token, test_project, test_task):
        resp = client.get(
            f"/api/projects/{test_project.id}/tasks?assignee_id={editor_user.id}",
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 200
        for t in resp.json():
            assert t["assignee_id"] == editor_user.id


class TestGetTask:
    def test_get_task(self, client, editor_token, test_task):
        resp = client.get(f"/api/tasks/{test_task.id}", headers=auth_header(editor_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Test Task"
        assert data["id"] == test_task.id

    def test_get_task_not_found(self, client, editor_token):
        resp = client.get("/api/tasks/9999", headers=auth_header(editor_token))
        assert resp.status_code == 404


class TestUpdateTask:
    def test_update_task_status_kanban(self, client, editor_token, test_task):
        """Simulate a Kanban drag: change status from todo to in-progress."""
        resp = client.put(
            f"/api/tasks/{test_task.id}",
            json={"status": "in-progress"},
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "in-progress"

    def test_update_task_multiple_fields(self, client, editor_token, test_task):
        resp = client.put(
            f"/api/tasks/{test_task.id}",
            json={"title": "Updated", "priority": "urgent"},
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Updated"
        assert data["priority"] == "urgent"

    def test_update_task_not_found(self, client, editor_token):
        resp = client.put(
            "/api/tasks/9999",
            json={"title": "Ghost"},
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 404


class TestDeleteTask:
    def test_delete_task(self, client, editor_token, test_task):
        resp = client.delete(f"/api/tasks/{test_task.id}", headers=auth_header(editor_token))
        assert resp.status_code == 204

        # Verify deleted
        resp = client.get(f"/api/tasks/{test_task.id}", headers=auth_header(editor_token))
        assert resp.status_code == 404

    def test_delete_task_not_found(self, client, editor_token):
        resp = client.delete("/api/tasks/9999", headers=auth_header(editor_token))
        assert resp.status_code == 404


class TestTaskRBAC:
    """Role-based access control: viewer can read, editor can mutate, admin can do all."""

    def test_viewer_can_read_tasks(self, client, viewer_token, test_project, test_task):
        resp = client.get(
            f"/api/projects/{test_project.id}/tasks",
            headers=auth_header(viewer_token),
        )
        assert resp.status_code == 200

    def test_viewer_can_get_task(self, client, viewer_token, test_task):
        resp = client.get(f"/api/tasks/{test_task.id}", headers=auth_header(viewer_token))
        assert resp.status_code == 200

    def test_viewer_cannot_create_task(self, client, viewer_token, test_project):
        resp = client.post(
            f"/api/projects/{test_project.id}/tasks",
            json={"title": "Blocked", "project_id": test_project.id},
            headers=auth_header(viewer_token),
        )
        assert resp.status_code == 403

    def test_viewer_cannot_update_task(self, client, viewer_token, test_task):
        resp = client.put(
            f"/api/tasks/{test_task.id}",
            json={"title": "Blocked"},
            headers=auth_header(viewer_token),
        )
        assert resp.status_code == 403

    def test_viewer_cannot_delete_task(self, client, viewer_token, test_task):
        resp = client.delete(f"/api/tasks/{test_task.id}", headers=auth_header(viewer_token))
        assert resp.status_code == 403

    def test_editor_can_mutate_task(self, client, editor_token, test_task):
        resp = client.put(
            f"/api/tasks/{test_task.id}",
            json={"title": "Editor Updated"},
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Editor Updated"

    def test_admin_can_create_task(self, client, admin_token, test_project):
        resp = client.post(
            f"/api/projects/{test_project.id}/tasks",
            json={"title": "Admin Task", "project_id": test_project.id},
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 201

    def test_admin_can_update_task(self, client, admin_token, test_task):
        resp = client.put(
            f"/api/tasks/{test_task.id}",
            json={"title": "Admin Updated"},
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200

    def test_admin_can_delete_task(self, client, admin_token, test_task):
        resp = client.delete(f"/api/tasks/{test_task.id}", headers=auth_header(admin_token))
        assert resp.status_code == 204
