"""
Pytest configuration and shared fixtures for the API test suite.

Sets required environment variables BEFORE any application code is imported,
patches external SDKs (livekit) via sys.modules, and provides a FastAPI
TestClient fixture.

Author: Pritam
Date: 2026-10-12
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

# ---------------------------------------------------------------------------
# 1. Inject env vars BEFORE any application module is imported.
# ---------------------------------------------------------------------------
os.environ.setdefault("LIVEKIT_API_KEY", "test-key")
os.environ.setdefault("LIVEKIT_API_SECRET", "test-secret-32chars-padding12345")
os.environ.setdefault("LIVEKIT_URL", "wss://test.livekit.io")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

# ---------------------------------------------------------------------------
# 2. Make `backend/api` importable without a package prefix.
# ---------------------------------------------------------------------------
_API_DIR = os.path.join(os.path.dirname(__file__), "..", )
_API_DIR = os.path.abspath(_API_DIR)
if _API_DIR not in sys.path:
    sys.path.insert(0, _API_DIR)

# ---------------------------------------------------------------------------
# 3. Stub out the `livekit` SDK so tests don't need the real package.
# ---------------------------------------------------------------------------
_livekit_mock = MagicMock()
_livekit_api_mock = MagicMock()

# AccessToken and VideoGrants need to behave like fluent builders.
_access_token_instance = MagicMock()
_access_token_instance.with_identity.return_value = _access_token_instance
_access_token_instance.with_name.return_value = _access_token_instance
_access_token_instance.with_ttl.return_value = _access_token_instance
_access_token_instance.with_grants.return_value = _access_token_instance
_access_token_instance.to_jwt.return_value = "mock-jwt-token"

_livekit_api_mock.AccessToken.return_value = _access_token_instance
_livekit_api_mock.VideoGrants = MagicMock()

# LiveKitAPI needs to support `async with LiveKitAPI(...) as lk:` in the token router.
_livekit_api_instance = MagicMock()
_livekit_api_instance.agent_dispatch = MagicMock()
_livekit_api_instance.agent_dispatch.create_dispatch = AsyncMock(return_value=MagicMock(id="AD_test"))
_livekit_api_instance.__aenter__ = AsyncMock(return_value=_livekit_api_instance)
_livekit_api_instance.__aexit__ = AsyncMock(return_value=False)
_livekit_api_mock.LiveKitAPI.return_value = _livekit_api_instance
_livekit_api_mock.CreateAgentDispatchRequest = MagicMock()

sys.modules.setdefault("livekit", _livekit_mock)
sys.modules.setdefault("livekit.api", _livekit_api_mock)

# ---------------------------------------------------------------------------
# 4. Fixtures
# ---------------------------------------------------------------------------
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    """Return a FastAPI TestClient bound to the application."""
    # Import here so env vars and sys.modules patches are already in place.
    from main import app  # noqa: PLC0415

    return TestClient(app)
