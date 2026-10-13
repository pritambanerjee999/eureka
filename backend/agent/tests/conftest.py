"""
Pytest configuration and shared fixtures for the agent test suite.

Sets required environment variables BEFORE any application code is imported,
then stubs the entire livekit package tree so the real SDK is not needed.

Author: Pritam
Date: 2026-10-12
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

# ---------------------------------------------------------------------------
# 1. Env vars BEFORE any imports
# ---------------------------------------------------------------------------
os.environ.setdefault("LIVEKIT_API_KEY", "test-key")
os.environ.setdefault("LIVEKIT_API_SECRET", "test-secret-32chars-padding12345")
os.environ.setdefault("LIVEKIT_URL", "wss://test.livekit.io")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

# ---------------------------------------------------------------------------
# 2. Make `backend/agent` importable without a package prefix.
# ---------------------------------------------------------------------------
_AGENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _AGENT_DIR not in sys.path:
    sys.path.insert(0, _AGENT_DIR)

# ---------------------------------------------------------------------------
# 3. Stub the entire livekit SDK tree.
#    We need to do this before any agent module is imported.
# ---------------------------------------------------------------------------

# Base livekit namespace
livekit_mock = MagicMock()

# livekit.agents — Agent is a real class so PhysicsTutorAgent can inherit from it
agent_mock = MagicMock()


class Agent:
    """Minimal stand-in for livekit.agents.Agent."""

    def __init__(self, **kwargs):
        self._instructions = kwargs.get("instructions", "")
        self._chat_ctx = kwargs.get("chat_ctx")


agent_mock.Agent = Agent
agent_mock.RunContext = MagicMock

# livekit.agents.llm — function_tool must be a no-op decorator so async methods survive
llm_mock = MagicMock()
llm_mock.function_tool = lambda f: f  # identity decorator

# livekit.api
api_mock = MagicMock()

# livekit.plugins.*
plugins_mock = MagicMock()
plugins_openai_mock = MagicMock()
plugins_silero_mock = MagicMock()

# Register every submodule that agent code imports
sys.modules.setdefault("livekit", livekit_mock)
sys.modules.setdefault("livekit.agents", agent_mock)
sys.modules.setdefault("livekit.agents.llm", llm_mock)
sys.modules.setdefault("livekit.api", api_mock)
sys.modules.setdefault("livekit.plugins", plugins_mock)
sys.modules.setdefault("livekit.plugins.openai", plugins_openai_mock)
sys.modules.setdefault("livekit.plugins.silero", plugins_silero_mock)
