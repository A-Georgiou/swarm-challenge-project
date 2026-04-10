"""Tests for /api/users endpoints: list, get, update, delete."""

import pytest
from tests.conftest import auth_header


class TestListUsers:
    def test_list_users(self, client, admin_user, editor_user, admin_token):
        resp = client.get("/api/users/", headers=auth_header(admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
        usernames = [u["username"] for u in data]
        assert "admin" in usernames
        assert "editor" in usernames

    def test_list_users_unauthenticated(self, client):
        resp = client.get("/api/users/")
        assert resp.status_code == 401


class TestGetUser:
    def test_get_user(self, client, admin_user, admin_token):
        resp = client.get(f"/api/users/{admin_user.id}", headers=auth_header(admin_token))
        assert resp.status_code == 200
        assert resp.json()["username"] == "admin"

    def test_get_user_not_found(self, client, admin_user, admin_token):
        resp = client.get("/api/users/9999", headers=auth_header(admin_token))
        assert resp.status_code == 404


class TestUpdateUser:
    def test_update_user_admin(self, client, admin_user, editor_user, admin_token):
        resp = client.put(
            f"/api/users/{editor_user.id}",
            json={"username": "editor_renamed"},
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "editor_renamed"

    def test_update_user_forbidden_editor(self, client, admin_user, editor_user, editor_token):
        resp = client.put(
            f"/api/users/{admin_user.id}",
            json={"username": "hacked"},
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 403

    def test_update_user_forbidden_viewer(self, client, admin_user, viewer_user, viewer_token):
        resp = client.put(
            f"/api/users/{admin_user.id}",
            json={"username": "hacked"},
            headers=auth_header(viewer_token),
        )
        assert resp.status_code == 403

    def test_update_user_not_found(self, client, admin_user, admin_token):
        resp = client.put(
            "/api/users/9999",
            json={"username": "ghost"},
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 404

    def test_update_user_duplicate_username(self, client, admin_user, editor_user, admin_token):
        resp = client.put(
            f"/api/users/{editor_user.id}",
            json={"username": "admin"},
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 400
        assert "Username already taken" in resp.json()["detail"]

    def test_update_user_duplicate_email(self, client, admin_user, editor_user, admin_token):
        resp = client.put(
            f"/api/users/{editor_user.id}",
            json={"email": "admin@test.com"},
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 400
        assert "Email already taken" in resp.json()["detail"]


class TestDeleteUser:
    def test_delete_user_admin(self, client, admin_user, editor_user, admin_token):
        resp = client.delete(
            f"/api/users/{editor_user.id}",
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 204

        # Confirm deleted
        resp = client.get(f"/api/users/{editor_user.id}", headers=auth_header(admin_token))
        assert resp.status_code == 404

    def test_delete_user_prevent_self_delete(self, client, admin_user, admin_token):
        resp = client.delete(
            f"/api/users/{admin_user.id}",
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 400
        assert "Cannot delete yourself" in resp.json()["detail"]

    def test_delete_user_forbidden_editor(self, client, admin_user, editor_user, editor_token):
        resp = client.delete(
            f"/api/users/{admin_user.id}",
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 403

    def test_delete_user_forbidden_viewer(self, client, admin_user, viewer_user, viewer_token):
        resp = client.delete(
            f"/api/users/{admin_user.id}",
            headers=auth_header(viewer_token),
        )
        assert resp.status_code == 403

    def test_delete_user_not_found(self, client, admin_user, admin_token):
        resp = client.delete(
            "/api/users/9999",
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 404
