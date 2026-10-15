"""
Integration tests for the /auth router.

The asyncpg pool is mocked so no real PostgreSQL instance is needed.

Author: Pritam
Date: 2026-10-12
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest
from fastapi.testclient import TestClient

from services.auth_service import create_access_token, hash_password


@pytest.fixture()
def auth_client():
    """Yield (client, mock_conn) with routers.auth.get_pool patched."""
    conn = AsyncMock()
    conn.execute = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)

    @asynccontextmanager
    async def _acquire():
        yield conn

    pool = MagicMock()
    pool.acquire = _acquire

    with patch("routers.auth.get_pool", new_callable=AsyncMock, return_value=pool):
        from main import app
        with TestClient(app) as c:
            yield c, conn


class TestRegister:
    def test_register_returns_token(self, auth_client):
        """A valid registration should insert a user and return a usable token."""
        client, conn = auth_client
        resp = client.post("/auth/register", json={"username": "Alice", "password": "password123"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "alice"
        assert data["token_type"] == "bearer"
        me = client.get("/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
        assert me.json() == {"username": "alice"}

    def test_register_stores_hash_not_plaintext(self, auth_client):
        """The INSERT should receive a scrypt hash, never the plaintext password."""
        client, conn = auth_client
        client.post("/auth/register", json={"username": "alice", "password": "password123"})
        sql, username, stored = conn.execute.call_args[0]
        assert "INSERT INTO users" in sql
        assert username == "alice"
        assert stored.startswith("scrypt$")
        assert "password123" not in stored

    def test_duplicate_username_returns_409(self, auth_client):
        """A unique-constraint violation should map to 409."""
        client, conn = auth_client
        conn.execute.side_effect = asyncpg.UniqueViolationError("dup")
        resp = client.post("/auth/register", json={"username": "alice", "password": "password123"})
        assert resp.status_code == 409
        assert "taken" in resp.json()["detail"]

    def test_invalid_payload_returns_422(self, auth_client):
        """Schema validation failures should not touch the DB."""
        client, conn = auth_client
        resp = client.post("/auth/register", json={"username": "a", "password": "x"})
        assert resp.status_code == 422
        conn.execute.assert_not_called()


class TestLogin:
    def _row(self, username="alice", password="password123"):
        return {"username": username, "password_hash": hash_password(password)}

    def test_login_success(self, auth_client):
        """Correct credentials should return a token for the stored username."""
        client, conn = auth_client
        conn.fetchrow.return_value = self._row()
        resp = client.post("/auth/login", json={"username": "  ALICE ", "password": "password123"})
        assert resp.status_code == 200
        assert resp.json()["username"] == "alice"
        assert conn.fetchrow.call_args[0][1] == "alice"

    def test_wrong_password_returns_401(self, auth_client):
        """A bad password should be rejected."""
        client, conn = auth_client
        conn.fetchrow.return_value = self._row()
        resp = client.post("/auth/login", json={"username": "alice", "password": "nope"})
        assert resp.status_code == 401

    def test_unknown_user_returns_401_same_message(self, auth_client):
        """Unknown users get the same error as bad passwords (no user enumeration)."""
        client, conn = auth_client
        conn.fetchrow.return_value = None
        resp = client.post("/auth/login", json={"username": "ghost", "password": "password123"})
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid username or password"


class TestMe:
    def test_me_requires_token(self, auth_client):
        """GET /auth/me without a token should be 401."""
        client, _ = auth_client
        assert client.get("/auth/me").status_code == 401

    def test_me_rejects_bad_token(self, auth_client):
        """GET /auth/me with an invalid token should be 401."""
        client, _ = auth_client
        resp = client.get("/auth/me", headers={"Authorization": "Bearer garbage"})
        assert resp.status_code == 401

    def test_me_returns_username(self, auth_client):
        """GET /auth/me with a valid token returns its username."""
        client, _ = auth_client
        token = create_access_token("bob")
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.json() == {"username": "bob"}
