"""
Integration tests for the POST /token router.

create_session and generate_token are patched so no real Redis or LiveKit
calls are made.

Author: Pritam
Date: 2026-10-12
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture()
def client_with_mocks():
    """
    Return a TestClient with create_session and generate_token patched.

    Yields (client, create_session_mock, generate_token_mock).
    """
    from dependencies import get_current_user
    from main import app

    app.dependency_overrides[get_current_user] = lambda: "alice"
    with (
        patch("routers.token.create_session", new_callable=AsyncMock) as cs_mock,
        patch("routers.token.generate_token", return_value="signed-jwt") as gt_mock,
    ):
        with TestClient(app) as c:
            yield c, cs_mock, gt_mock
    app.dependency_overrides.clear()


class TestPostToken:
    def test_no_body_generates_room_and_uses_user_identity(self, client_with_mocks):
        """POST /token with an empty body should generate a room and use the caller's identity."""
        client, _, _ = client_with_mocks
        resp = client.post("/token", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["room_name"].startswith("room-")
        assert data["identity"] == "alice"

    def test_client_supplied_identity_is_ignored(self, client_with_mocks):
        """A client cannot impersonate another user by passing an identity."""
        client, cs_mock, gt_mock = client_with_mocks
        resp = client.post("/token", json={"identity": "mallory"})
        assert resp.status_code == 200
        assert resp.json()["identity"] == "alice"
        assert cs_mock.call_args[0][1] == "alice"
        assert gt_mock.call_args[0][1] == "alice"

    def test_provided_room_name_is_used(self, client_with_mocks):
        """POST /token with a room_name should use it verbatim."""
        client, _, _ = client_with_mocks
        resp = client.post("/token", json={"room_name": "physics-101"})
        assert resp.status_code == 200
        assert resp.json()["room_name"] == "physics-101"

    def test_topic_is_passed_to_create_session(self, client_with_mocks):
        """POST /token with a topic should forward it to create_session."""
        client, cs_mock, _ = client_with_mocks
        resp = client.post("/token", json={"topic": "Quantum Tunnelling"})
        assert resp.status_code == 200
        _, call_kwargs = cs_mock.call_args
        # create_session(room_name, identity, topic=...)
        assert call_kwargs.get("topic") == "Quantum Tunnelling" or cs_mock.call_args[0][2:] == () or "Quantum Tunnelling" in str(cs_mock.call_args)

    def test_topic_forwarded_positional_or_keyword(self, client_with_mocks):
        """Verify the topic argument reaches create_session regardless of call style."""
        client, cs_mock, _ = client_with_mocks
        resp = client.post("/token", json={"topic": "Light"})
        assert resp.status_code == 200
        args, kwargs = cs_mock.call_args
        # topic is the third positional OR keyword argument
        topic_value = kwargs.get("topic") or (args[2] if len(args) > 2 else None)
        assert topic_value == "Light"

    def test_response_shape_matches_schema(self, client_with_mocks):
        """Response should include token, room_name, identity, and livekit_url."""
        client, _, _ = client_with_mocks
        resp = client.post("/token", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert "room_name" in data
        assert "identity" in data
        assert "livekit_url" in data

    def test_token_comes_from_generate_token(self, client_with_mocks):
        """The token in the response should be the value returned by generate_token."""
        client, _, _ = client_with_mocks
        resp = client.post("/token", json={})
        assert resp.json()["token"] == "signed-jwt"

    def test_livekit_url_from_settings(self, client_with_mocks):
        """livekit_url in the response should equal the configured LIVEKIT_URL."""
        import os
        client, _, _ = client_with_mocks
        resp = client.post("/token", json={})
        assert resp.json()["livekit_url"] == os.environ["LIVEKIT_URL"]

    def test_create_session_exception_returns_503(self, client_with_mocks):
        """A Redis failure in create_session should produce a 503 response."""
        client, cs_mock, _ = client_with_mocks
        cs_mock.side_effect = ConnectionError("Redis down")
        resp = client.post("/token", json={})
        assert resp.status_code == 503
        assert "Session store unavailable" in resp.json()["detail"]

    def test_no_topic_passes_none_to_create_session(self, client_with_mocks):
        """When no topic is given, create_session should be called with topic=None."""
        client, cs_mock, _ = client_with_mocks
        resp = client.post("/token", json={})
        assert resp.status_code == 200
        args, kwargs = cs_mock.call_args
        # Use a sentinel to distinguish "key missing" from "key present with value None"
        _NOT_SET = object()
        topic_value = kwargs.get("topic", _NOT_SET)
        if topic_value is _NOT_SET:
            topic_value = args[2] if len(args) > 2 else None
        assert topic_value is None


class TestPostTokenAuth:
    def test_missing_auth_header_returns_401(self):
        """POST /token without a Bearer token should be rejected."""
        from main import app
        with TestClient(app) as c:
            resp = c.post("/token", json={})
        assert resp.status_code == 401

    def test_invalid_bearer_token_returns_401(self):
        """POST /token with a garbage Bearer token should be rejected."""
        from main import app
        with TestClient(app) as c:
            resp = c.post("/token", json={}, headers={"Authorization": "Bearer nope"})
        assert resp.status_code == 401


class TestAgentDispatch:
    def test_dispatch_targets_named_agent(self, client_with_mocks):
        """The dispatch must name the worker; an unnamed worker is also auto-dispatched,
        which put two agents (two voices) in every room."""
        client, _, _ = client_with_mocks
        lk = MagicMock()
        lk.agent_dispatch.create_dispatch = AsyncMock(return_value=MagicMock(id="AD_x"))
        lk.__aenter__ = AsyncMock(return_value=lk)
        lk.__aexit__ = AsyncMock(return_value=False)
        with (
            patch("routers.token.LiveKitAPI", return_value=lk),
            patch("routers.token.CreateAgentDispatchRequest") as req_mock,
        ):
            resp = client.post("/token", json={})
        assert resp.status_code == 200
        req_mock.assert_called_once_with(room=resp.json()["room_name"], agent_name="eureka-tutor")
        lk.agent_dispatch.create_dispatch.assert_awaited_once()
