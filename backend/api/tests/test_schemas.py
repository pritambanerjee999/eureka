"""
Unit tests for the Pydantic request/response schemas.

Author: Pritam
Date: 2026-10-12
"""

import pytest
from pydantic import ValidationError

from models.schemas import RegisterRequest, TokenRequest, TokenResponse


class TestTokenRequest:
    def test_all_fields_none_by_default(self):
        """TokenRequest with no arguments should have all fields set to None."""
        req = TokenRequest()
        assert req.room_name is None
        assert req.topic is None

    def test_all_fields_populated(self):
        """TokenRequest should accept and store all optional fields."""
        req = TokenRequest(room_name="room-abc", topic="Light")
        assert req.room_name == "room-abc"
        assert req.topic == "Light"

    def test_only_topic_provided(self):
        """TokenRequest with only topic should leave room_name as None."""
        req = TokenRequest(topic="Sound Waves")
        assert req.topic == "Sound Waves"
        assert req.room_name is None

    def test_only_room_name_provided(self):
        """TokenRequest with only room_name should leave topic as None."""
        req = TokenRequest(room_name="my-room")
        assert req.room_name == "my-room"
        assert req.topic is None

    def test_special_topic_assess(self):
        """TokenRequest should accept the special '__assess__' topic value."""
        req = TokenRequest(topic="__assess__")
        assert req.topic == "__assess__"

    def test_special_topic_open(self):
        """TokenRequest should accept the special '__open__' topic value."""
        req = TokenRequest(topic="__open__")
        assert req.topic == "__open__"


class TestTokenResponse:
    def test_round_trip(self):
        """TokenResponse should serialise and deserialise correctly."""
        resp = TokenResponse(
            token="jwt-abc",
            room_name="room-1",
            identity="user-1",
            livekit_url="wss://test.livekit.io",
        )
        assert resp.token == "jwt-abc"
        assert resp.room_name == "room-1"
        assert resp.identity == "user-1"
        assert resp.livekit_url == "wss://test.livekit.io"

    def test_all_fields_required(self):
        """TokenResponse should raise a ValidationError when a field is missing."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            TokenResponse(token="t", room_name="r")  # missing identity + livekit_url

    def test_model_dump(self):
        """TokenResponse.model_dump() should return a plain dict."""
        resp = TokenResponse(
            token="t",
            room_name="r",
            identity="i",
            livekit_url="wss://x",
        )
        d = resp.model_dump()
        assert isinstance(d, dict)
        assert d["token"] == "t"
        assert d["livekit_url"] == "wss://x"


class TestRegisterRequest:
    def test_username_is_trimmed_and_lowercased(self):
        """Usernames should be normalised before validation."""
        req = RegisterRequest(username="  Alice_01 ", password="password123")
        assert req.username == "alice_01"

    @pytest.mark.parametrize("username", ["ab", "a" * 33, "has space", "bad!char", ""])
    def test_invalid_usernames_rejected(self, username):
        """Usernames outside 3-32 chars or with disallowed characters should fail."""
        with pytest.raises(ValidationError):
            RegisterRequest(username=username, password="password123")

    def test_boundary_username_lengths_accepted(self):
        """3- and 32-character usernames are the inclusive bounds."""
        assert RegisterRequest(username="abc", password="password123").username == "abc"
        assert RegisterRequest(username="a" * 32, password="password123").username == "a" * 32

    def test_reserved_user_prefix_rejected(self):
        """The 'user-' prefix is reserved for legacy anonymous identities."""
        with pytest.raises(ValidationError, match="reserved"):
            RegisterRequest(username="user-abc", password="password123")

    def test_short_password_rejected(self):
        """Passwords under 8 characters should fail."""
        with pytest.raises(ValidationError):
            RegisterRequest(username="alice", password="short")

    def test_long_password_rejected(self):
        """Passwords over 128 characters should fail."""
        with pytest.raises(ValidationError):
            RegisterRequest(username="alice", password="x" * 129)
