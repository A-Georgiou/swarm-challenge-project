"""Tests for comment endpoints: create, list, update, delete."""

import pytest
from tests.conftest import auth_header
from app.models.comment import Comment


class TestCreateComment:
    def test_create_comment(self, client, editor_user, editor_token, test_task):
        resp = client.post(
            f"/api/tasks/{test_task.id}/comments",
            json={"content": "Great work!", "task_id": test_task.id},
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "Great work!"
        assert data["user_id"] == editor_user.id
        assert data["task_id"] == test_task.id

    def test_create_comment_task_not_found(self, client, editor_token):
        resp = client.post(
            "/api/tasks/9999/comments",
            json={"content": "Hello", "task_id": 9999},
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 404

    def test_create_comment_viewer_can_comment(self, client, viewer_user, viewer_token, test_task):
        """Any authenticated user (including viewer) can create comments."""
        resp = client.post(
            f"/api/tasks/{test_task.id}/comments",
            json={"content": "Viewer comment", "task_id": test_task.id},
            headers=auth_header(viewer_token),
        )
        assert resp.status_code == 201
        assert resp.json()["user_id"] == viewer_user.id


class TestListComments:
    def test_list_comments(self, client, editor_user, editor_token, test_task, db):
        db.add(Comment(content="Comment 1", user_id=editor_user.id, task_id=test_task.id))
        db.add(Comment(content="Comment 2", user_id=editor_user.id, task_id=test_task.id))
        db.commit()

        resp = client.get(
            f"/api/tasks/{test_task.id}/comments",
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_list_comments_task_not_found(self, client, editor_token):
        resp = client.get(
            "/api/tasks/9999/comments",
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 404


class TestUpdateComment:
    def test_update_comment_author(self, client, editor_user, editor_token, test_task, db):
        comment = Comment(content="Original", user_id=editor_user.id, task_id=test_task.id)
        db.add(comment)
        db.commit()
        db.refresh(comment)

        resp = client.put(
            f"/api/comments/{comment.id}",
            json={"content": "Updated"},
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 200
        assert resp.json()["content"] == "Updated"

    def test_update_comment_not_author(self, client, editor_user, admin_token, test_task, db):
        comment = Comment(content="Editor's comment", user_id=editor_user.id, task_id=test_task.id)
        db.add(comment)
        db.commit()
        db.refresh(comment)

        resp = client.put(
            f"/api/comments/{comment.id}",
            json={"content": "Admin tries to edit"},
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 403

    def test_update_comment_not_found(self, client, editor_token):
        resp = client.put(
            "/api/comments/9999",
            json={"content": "Ghost"},
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 404


class TestDeleteComment:
    def test_delete_comment_author(self, client, editor_user, editor_token, test_task, db):
        comment = Comment(content="Delete me", user_id=editor_user.id, task_id=test_task.id)
        db.add(comment)
        db.commit()
        db.refresh(comment)

        resp = client.delete(
            f"/api/comments/{comment.id}",
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 204

    def test_delete_comment_admin(self, client, admin_user, editor_user, admin_token, test_task, db):
        """Admin can delete any comment, even if not the author."""
        comment = Comment(content="Editor wrote this", user_id=editor_user.id, task_id=test_task.id)
        db.add(comment)
        db.commit()
        db.refresh(comment)

        resp = client.delete(
            f"/api/comments/{comment.id}",
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 204

    def test_delete_comment_forbidden(self, client, admin_user, editor_user, viewer_token, test_task, db):
        """A non-author, non-admin cannot delete a comment."""
        comment = Comment(content="Editor wrote this", user_id=editor_user.id, task_id=test_task.id)
        db.add(comment)
        db.commit()
        db.refresh(comment)

        resp = client.delete(
            f"/api/comments/{comment.id}",
            headers=auth_header(viewer_token),
        )
        assert resp.status_code == 403

    def test_delete_comment_not_found(self, client, editor_token):
        resp = client.delete(
            "/api/comments/9999",
            headers=auth_header(editor_token),
        )
        assert resp.status_code == 404
