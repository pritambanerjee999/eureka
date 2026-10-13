"""
Integration tests for the history and notes router endpoints.

The asyncpg pool is mocked so no real PostgreSQL instance is needed.

Author: Pritam
Date: 2026-10-12
"""

import datetime
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from fastapi.testclient import TestClient


def _make_mock_conn(fetch_result=None, fetchrow_result=None, execute_result=None):
    """Build a mock asyncpg connection pre-configured with return values."""
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=fetch_result or [])
    conn.fetchrow = AsyncMock(return_value=fetchrow_result)
    conn.execute = AsyncMock(return_value=execute_result)
    return conn


def _make_mock_pool(conn):
    """Wrap a mock connection in a mock pool whose acquire() is an async CM."""

    @asynccontextmanager
    async def _acquire():
        yield conn

    pool = MagicMock()
    pool.acquire = _acquire
    return pool


@pytest.fixture()
def fresh_client():
    """
    Return a TestClient with the history router's get_pool patched and the
    caller authenticated as whatever identity the test requests.

    Yields (client, mock_conn) so individual tests can customise return values.
    """
    from dependencies import get_current_user
    from main import app

    conn = _make_mock_conn()
    pool = _make_mock_pool(conn)

    # Treat the path identity as the authenticated user so ownership checks pass.
    def _as_path_identity(request: Request) -> str:
        return request.path_params.get("identity", "")

    app.dependency_overrides[get_current_user] = _as_path_identity
    with patch("routers.history.get_pool", new_callable=AsyncMock, return_value=pool):
        with TestClient(app) as c:
            yield c, conn
    app.dependency_overrides.clear()


class TestGetHistory:
    def test_empty_history_returns_empty_list(self, fresh_client):
        """GET /history/{identity} with no rows should return an empty messages list."""
        client, conn = fresh_client
        conn.fetch.return_value = []

        resp = client.get("/history/user-abc")

        assert resp.status_code == 200
        data = resp.json()
        assert data["identity"] == "user-abc"
        assert data["messages"] == []

    def test_history_with_rows_returns_messages(self, fresh_client):
        """GET /history/{identity} with rows should include role/content/room/timestamp."""
        client, conn = fresh_client
        ts = datetime.datetime(2026, 10, 12, 10, 0, 0, tzinfo=datetime.timezone.utc)

        # asyncpg rows behave like dicts; we simulate with MagicMock subscript.
        row = MagicMock()
        row.__getitem__ = lambda self, key: {
            "role": "user",
            "content": "What is gravity?",
            "room_name": "room-1",
            "created_at": ts,
        }[key]
        conn.fetch.return_value = [row]

        resp = client.get("/history/user-abc")

        assert resp.status_code == 200
        messages = resp.json()["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "What is gravity?"
        assert messages[0]["room_name"] == "room-1"
        assert "2026-10-12" in messages[0]["timestamp"]

    def test_history_identity_in_response(self, fresh_client):
        """GET /history/{identity} response should echo the identity back."""
        client, _ = fresh_client
        resp = client.get("/history/unique-user-99")
        assert resp.json()["identity"] == "unique-user-99"


class TestGetNotes:
    def test_get_notes_returns_notes_list(self, fresh_client):
        """GET /notes/{identity} should return a notes list with room/content/updated_at."""
        client, conn = fresh_client
        ts = datetime.datetime(2026, 10, 12, 11, 0, 0, tzinfo=datetime.timezone.utc)

        row = MagicMock()
        row.__getitem__ = lambda self, key: {
            "room_name": "room-2",
            "content": "Remember F=ma",
            "updated_at": ts,
        }[key]
        conn.fetch.return_value = [row]

        resp = client.get("/notes/user-xyz")

        assert resp.status_code == 200
        data = resp.json()
        assert "notes" in data
        notes = data["notes"]
        assert len(notes) == 1
        assert notes[0]["room_name"] == "room-2"
        assert notes[0]["content"] == "Remember F=ma"
        assert "2026-10-12" in notes[0]["updated_at"]

    def test_get_notes_empty(self, fresh_client):
        """GET /notes/{identity} with no notes should return an empty list."""
        client, conn = fresh_client
        conn.fetch.return_value = []
        resp = client.get("/notes/user-no-notes")
        assert resp.status_code == 200
        assert resp.json()["notes"] == []


class TestPutNotes:
    def test_put_notes_calls_execute_upsert(self, fresh_client):
        """PUT /notes/{identity}/{room_name} should execute the upsert SQL."""
        client, conn = fresh_client

        resp = client.put(
            "/notes/user-z/room-0000000a",
            json={"content": "Newton's first law notes"},
        )

        assert resp.status_code == 200
        assert resp.json().get("saved") is True
        conn.execute.assert_called_once()
        sql, *args = conn.execute.call_args[0]
        assert "INSERT INTO notes" in sql
        assert "ON CONFLICT" in sql

    def test_put_notes_passes_content(self, fresh_client):
        """PUT /notes should pass the provided content to the SQL execute call."""
        client, conn = fresh_client

        resp = client.put(
            "/notes/user-w/room-0000000b",
            json={"content": "Energy is conserved"},
        )

        assert resp.status_code == 200
        call_args = conn.execute.call_args[0]
        # call_args is (sql, identity, room_name, content)
        assert "Energy is conserved" in call_args

    def test_put_notes_empty_body_uses_empty_string(self, fresh_client):
        """PUT /notes with no 'content' key should default to empty string."""
        client, conn = fresh_client

        resp = client.put("/notes/user-v/room-0000000c", json={})

        assert resp.status_code == 200
        call_args = conn.execute.call_args[0]
        # The empty string should be one of the SQL parameters
        assert "" in call_args


class TestNotesValidation:
    @pytest.mark.parametrize("room", ["room-z", "anything", "room-XYZ12345", "room-" + "a" * 33])
    def test_invalid_room_name_rejected(self, fresh_client, room):
        """Only server-generated room names are accepted, so notes can't be spammed under arbitrary keys."""
        client, conn = fresh_client
        resp = client.put(f"/notes/alice/{room}", json={"content": "x"})
        assert resp.status_code == 422
        conn.execute.assert_not_called()

    def test_legacy_and_current_room_names_accepted(self, fresh_client):
        client, _ = fresh_client
        assert client.put("/notes/alice/room-1a2b3c4d", json={"content": "x"}).status_code == 200
        assert client.put("/notes/alice/room-" + "f" * 32, json={"content": "x"}).status_code == 200

    def test_non_string_content_returns_422(self, fresh_client):
        """A non-string content value is a validation error, not a 500."""
        client, conn = fresh_client
        assert client.put("/notes/alice/room-1a2b3c4d", json={"content": 123}).status_code == 422
        conn.execute.assert_not_called()

    def test_oversized_content_returns_422(self, fresh_client):
        client, conn = fresh_client
        resp = client.put("/notes/alice/room-1a2b3c4d", json={"content": "x" * 20_001})
        assert resp.status_code == 422
        conn.execute.assert_not_called()


class TestHistoryAuth:
    @pytest.fixture()
    def alice_client(self):
        """TestClient authenticated as 'alice' with a mocked pool."""
        from dependencies import get_current_user
        from main import app

        conn = _make_mock_conn()
        app.dependency_overrides[get_current_user] = lambda: "alice"
        with patch("routers.history.get_pool", new_callable=AsyncMock, return_value=_make_mock_pool(conn)):
            with TestClient(app) as c:
                yield c, conn
        app.dependency_overrides.clear()

    @pytest.mark.parametrize(
        "method,path",
        [("get", "/history/bob"), ("get", "/notes/bob"), ("put", "/notes/bob/room-00000001")],
    )
    def test_other_users_data_is_forbidden(self, alice_client, method, path):
        """Accessing another user's history or notes should return 403 without touching the DB."""
        client, conn = alice_client
        resp = client.request(method, path, json={"content": "x"} if method == "put" else None)
        assert resp.status_code == 403
        conn.fetch.assert_not_called()
        conn.execute.assert_not_called()

    def test_own_history_is_allowed(self, alice_client):
        """The authenticated user can read their own history."""
        client, _ = alice_client
        assert client.get("/history/alice").status_code == 200

    @pytest.mark.parametrize(
        "method,path",
        [("get", "/history/alice"), ("get", "/notes/alice"), ("put", "/notes/alice/room-00000001")],
    )
    def test_unauthenticated_requests_return_401(self, method, path):
        """Requests without a Bearer token should be rejected."""
        from main import app
        with TestClient(app) as c:
            resp = c.request(method, path, json={"content": "x"} if method == "put" else None)
        assert resp.status_code == 401
