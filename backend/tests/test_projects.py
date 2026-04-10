"""Tests for /api/projects endpoints: create, list, get, update, delete."""

import pytest
from tests.conftest import auth_header


class TestCreateProject:
    def test_create_project_editor(self, client, editor_user, editor_token):
        resp = client.post(
            "/api/projects/",
            json={"name": "New Project", "description": "desc"},
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "New Project"
        assert data["created_by"] == editor_user.id

    def test_create_project_admin(self, client, admin_user, admin_token):
        resp = client.post(
            "/api/projects/",
            json={"name": "Admin Project"},
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 201
        assert resp.json()["created_by"] == admin_user.id

    def test_create_project_forbidden_viewer(self, client, viewer_user, viewer_token):
        resp = client.post(
            "/api/projects/",
            json={"name": "Viewer Project"},
            headers=auth_header(viewer_token),
        )
        assert resp.status_code == 403


class TestListProjects:
    def test_list_projects(self, client, admin_token, test_project):
        resp = client.get("/api/projects/", headers=auth_header(admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert any(p["name"] == "Test Project" for p in data)

    def test_list_projects_unauthenticated(self, client):
        resp = client.get("/api/projects/")
        assert resp.status_code == 401


class TestGetProject:
    def test_get_project(self, client, admin_token, test_project):
        resp = client.get(f"/api/projects/{test_project.id}", headers=auth_header(admin_token))
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test Project"

    def test_get_project_not_found(self, client, admin_token):
        resp = client.get("/api/projects/9999", headers=auth_header(admin_token))
        assert resp.status_code == 404


class TestUpdateProject:
    def test_update_project_creator(self, client, editor_token, test_project):
        resp = client.put(
            f"/api/projects/{test_project.id}",
            json={"name": "Updated Project"},
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Project"

    def test_update_project_admin(self, client, admin_token, test_project):
        resp = client.put(
            f"/api/projects/{test_project.id}",
            json={"description": "Updated by admin"},
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated by admin"

    def test_update_project_forbidden(self, client, viewer_token, test_project):
        resp = client.put(
            f"/api/projects/{test_project.id}",
            json={"name": "Hacked"},
            headers=auth_header(viewer_token),
        )
        assert resp.status_code == 403

    def test_update_project_not_found(self, client, admin_token):
        resp = client.put(
            "/api/projects/9999",
            json={"name": "Ghost"},
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 404


class TestDeleteProject:
    def test_delete_project_creator(self, client, editor_token, test_project):
        resp = client.delete(
            f"/api/projects/{test_project.id}",
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 204

    def test_delete_project_admin(self, client, admin_token, test_project):
        resp = client.delete(
            f"/api/projects/{test_project.id}",
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 204

    def test_delete_project_forbidden(self, client, viewer_token, test_project):
        resp = client.delete(
            f"/api/projects/{test_project.id}",
            headers=auth_header(viewer_token),
        )
        assert resp.status_code == 403

    def test_delete_project_cascade_tasks(self, client, editor_token, test_project, test_task, db):
        from app.models.task import Task
        task_id = test_task.id
        project_id = test_project.id

        # Verify the task exists
        assert db.query(Task).filter(Task.id == task_id).first() is not None

        resp = client.delete(
            f"/api/projects/{project_id}",
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 204

        # The task should be cascade-deleted
        db.expire_all()
        assert db.query(Task).filter(Task.id == task_id).first() is None
