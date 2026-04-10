"""Tests for /api/auth endpoints: register, login, me."""

import pytest
from tests.conftest import auth_header, make_expired_token, TEST_USER_PASSWORD


class TestRegister:
    def test_register_success(self, client):
        resp = client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "new@test.com",
            "password": TEST_USER_PASSWORD,
            "role": "editor",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@test.com"
        assert data["role"] == "editor"
        assert "id" in data

    def test_register_duplicate_username(self, client, admin_user):
        resp = client.post("/api/auth/register", json={
            "username": "admin",
            "email": "other@test.com",
            "password": TEST_USER_PASSWORD,
        })
        assert resp.status_code == 400
        assert "Username already registered" in resp.json()["detail"]

    def test_register_duplicate_email(self, client, admin_user):
        resp = client.post("/api/auth/register", json={
            "username": "unique",
            "email": "admin@test.com",
            "password": TEST_USER_PASSWORD,
        })
        assert resp.status_code == 400
        assert "Email already registered" in resp.json()["detail"]

    def test_register_weak_password(self, client):
        resp = client.post("/api/auth/register", json={
            "username": "weakpw",
            "email": "weak@test.com",
            "password": "short",  # < 6 chars
        })
        assert resp.status_code == 422  # Pydantic validation error


class TestLogin:
    def test_login_success(self, client, admin_user):
        resp = client.post("/api/auth/login", json={
            "username": "admin",
            "password": TEST_USER_PASSWORD,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, admin_user):
        resp = client.post("/api/auth/login", json={
            "username": "admin",
            "password": TEST_USER_PASSWORD + "wrong",
        })
        assert resp.status_code == 401
        assert "Incorrect username or password" in resp.json()["detail"]

    def test_login_nonexistent_user(self, client):
        resp = client.post("/api/auth/login", json={
            "username": "ghost",
            "password": TEST_USER_PASSWORD,
        })
        assert resp.status_code == 401


class TestGetMe:
    def test_get_me_authenticated(self, client, admin_user, admin_token):
        resp = client.get("/api/auth/me", headers=auth_header(admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "admin"
        assert data["role"] == "admin"

    def test_get_me_unauthenticated(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_get_me_expired_token(self, client, admin_user):
        token = make_expired_token(admin_user.id)
        resp = client.get("/api/auth/me", headers=auth_header(token))
        assert resp.status_code == 401
