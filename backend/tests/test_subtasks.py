"""Tests for subtask endpoints: create, list, update, delete."""

import pytest
from tests.conftest import auth_header
from app.models.subtask import Subtask


class TestCreateSubtask:
    def test_create_subtask(self, client, editor_token, test_task):
        resp = client.post(
            f"/api/tasks/{test_task.id}/subtasks",
            json={"title": "Subtask 1", "task_id": test_task.id},
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Subtask 1"
        assert data["completed"] is False
        assert data["task_id"] == test_task.id

    def test_create_subtask_task_not_found(self, client, editor_token):
        resp = client.post(
            "/api/tasks/9999/subtasks",
            json={"title": "Orphan", "task_id": 9999},
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 404

    def test_create_subtask_viewer_forbidden(self, client, viewer_token, test_task):
        resp = client.post(
            f"/api/tasks/{test_task.id}/subtasks",
            json={"title": "Blocked", "task_id": test_task.id},
            headers=auth_header(viewer_token),
        )
        assert resp.status_code == 403


class TestListSubtasks:
    def test_list_subtasks(self, client, editor_token, test_task, db):
        # Create two subtasks
        db.add(Subtask(title="Sub A", task_id=test_task.id))
        db.add(Subtask(title="Sub B", task_id=test_task.id))
        db.commit()

        resp = client.get(
            f"/api/tasks/{test_task.id}/subtasks",
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        titles = {s["title"] for s in data}
        assert titles == {"Sub A", "Sub B"}

    def test_list_subtasks_task_not_found(self, client, editor_token):
        resp = client.get(
            "/api/tasks/9999/subtasks",
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 404


class TestUpdateSubtask:
    def test_update_subtask_toggle_completed(self, client, editor_token, test_task, db):
        subtask = Subtask(title="Toggle Me", completed=False, task_id=test_task.id)
        db.add(subtask)
        db.commit()
        db.refresh(subtask)

        resp = client.put(
            f"/api/subtasks/{subtask.id}",
            json={"completed": True},
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 200
        assert resp.json()["completed"] is True

    def test_update_subtask_title(self, client, editor_token, test_task, db):
        subtask = Subtask(title="Old Title", task_id=test_task.id)
        db.add(subtask)
        db.commit()
        db.refresh(subtask)

        resp = client.put(
            f"/api/subtasks/{subtask.id}",
            json={"title": "New Title"},
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"

    def test_update_subtask_not_found(self, client, editor_token):
        resp = client.put(
            "/api/subtasks/9999",
            json={"completed": True},
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 404


class TestDeleteSubtask:
    def test_delete_subtask(self, client, editor_token, test_task, db):
        subtask = Subtask(title="Delete Me", task_id=test_task.id)
        db.add(subtask)
        db.commit()
        db.refresh(subtask)
        subtask_id = subtask.id

        resp = client.delete(
            f"/api/subtasks/{subtask_id}",
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 204

        # Confirm deleted
        db.expire_all()
        assert db.query(Subtask).filter(Subtask.id == subtask_id).first() is None

    def test_delete_subtask_not_found(self, client, editor_token):
        resp = client.delete(
            "/api/subtasks/9999",
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 404
