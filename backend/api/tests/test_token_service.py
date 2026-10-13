"""
Unit tests for the token_service module.

The livekit.api module is already stubbed in conftest.py via sys.modules.

Author: Pritam
Date: 2026-10-12
"""

import sys
from unittest.mock import MagicMock, call

import pytest


class TestGenerateToken:
    def test_returns_string(self):
        """generate_token should return a non-empty string."""
        from services.token_service import generate_token

        result = generate_token("my-room", "user-abc")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_mock_jwt(self):
        """generate_token should return the value produced by AccessToken.to_jwt()."""
        from services.token_service import generate_token

        result = generate_token("room-x", "id-y")
        assert result == "mock-jwt-token"

    def test_access_token_created_with_settings_credentials(self):
        """AccessToken should be instantiated with the configured API key and secret."""
        import services.token_service as ts
        from unittest.mock import patch

        livekit_api_mock = sys.modules["livekit.api"]
        # Reset call counts so previous tests don't interfere
        livekit_api_mock.AccessToken.reset_mock()

        # Patch settings directly to guarantee deterministic values regardless
        # of what env vars are set in the container at test time.
        with patch.object(ts.settings, "LIVEKIT_API_KEY", "test-key"), \
             patch.object(ts.settings, "LIVEKIT_API_SECRET", "test-secret-value"):
            ts.generate_token("room-z", "user-z")

            livekit_api_mock.AccessToken.assert_called_once_with(
                api_key="test-key",
                api_secret="test-secret-value",
            )

    def test_with_identity_called_with_correct_identity(self):
        """The fluent builder should call with_identity with the provided identity."""
        from services.token_service import generate_token

        livekit_api_mock = sys.modules["livekit.api"]
        token_instance = livekit_api_mock.AccessToken.return_value
        token_instance.reset_mock()
        # Restore fluent chain after reset
        token_instance.with_identity.return_value = token_instance
        token_instance.with_name.return_value = token_instance
        token_instance.with_ttl.return_value = token_instance
        token_instance.with_grants.return_value = token_instance
        token_instance.to_jwt.return_value = "mock-jwt-token"

        generate_token("room-a", "user-b")

        token_instance.with_identity.assert_called_once_with("user-b")

    def test_with_grants_called_with_correct_room(self):
        """VideoGrants should be created with the correct room_name."""
        from services.token_service import generate_token

        livekit_api_mock = sys.modules["livekit.api"]
        livekit_api_mock.VideoGrants.reset_mock()

        generate_token("target-room", "any-user")

        call_kwargs = livekit_api_mock.VideoGrants.call_args
        assert call_kwargs is not None
        # VideoGrants(room_join=True, room=room_name, ...)
        assert call_kwargs.kwargs.get("room") == "target-room"
        assert call_kwargs.kwargs.get("room_join") is True
