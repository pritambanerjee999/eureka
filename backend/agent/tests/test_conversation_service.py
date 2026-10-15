"""
Unit tests for the conversation service (Redis + PostgreSQL turn routing).

Both stores are patched at the module level where conversation_service
imports them, so no real Redis or PostgreSQL is touched.

Author: Pritam
Date: 2026-10-12
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from services.conversation_service import load_room_turns, record_turn, turn_from_item


@pytest.fixture()
def stores():
    """Patch the Redis and PostgreSQL writers/readers used by the service."""
    with (
        patch("services.conversation_service.redis_service.append_message", new_callable=AsyncMock) as r_append,
        patch("services.conversation_service.redis_service.get_history", new_callable=AsyncMock) as r_hist,
        patch("services.conversation_service.db_service.append_message", new_callable=AsyncMock) as db_append,
    ):
        yield r_append, r_hist, db_append


class TestTurnFromItem:
    @pytest.mark.parametrize("role", ["user", "assistant"])
    def test_spoken_roles_extracted_and_stripped(self, role):
        """User and assistant messages yield (role, stripped text)."""
        item = SimpleNamespace(role=role, text_content="  hello  ")
        assert turn_from_item(item) == (role, "hello")

    @pytest.mark.parametrize("role", ["system", "developer", None])
    def test_non_spoken_roles_ignored(self, role):
        """System/developer prompts and role-less items are not transcript turns."""
        assert turn_from_item(SimpleNamespace(role=role, text_content="x")) is None

    @pytest.mark.parametrize("text", ["", "   ", None])
    def test_empty_text_ignored(self, text):
        """Empty or missing text (e.g. interrupted before speaking) is skipped."""
        assert turn_from_item(SimpleNamespace(role="user", text_content=text)) is None

    def test_item_without_attributes_ignored(self):
        """Non-message items such as agent handoffs are skipped."""
        assert turn_from_item(object()) is None


class TestRecordTurn:
    @pytest.mark.asyncio
    async def test_writes_to_both_stores(self, stores):
        """A turn goes to Redis keyed by room and PostgreSQL keyed by identity."""
        r_append, _, db_append = stores
        await record_turn("alice", "room-1", "user", "What is light?")
        r_append.assert_awaited_once_with("room-1", "user", "What is light?")
        db_append.assert_awaited_once_with("alice", "user", "What is light?", room_name="room-1")

    @pytest.mark.asyncio
    async def test_redis_failure_does_not_block_postgres(self, stores):
        """If Redis is down the durable write still happens and nothing raises."""
        r_append, _, db_append = stores
        r_append.side_effect = ConnectionError("redis down")
        await record_turn("alice", "room-1", "assistant", "Hi")
        db_append.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_postgres_failure_does_not_block_redis(self, stores):
        """If PostgreSQL is down the live Redis write still happens and nothing raises."""
        r_append, _, db_append = stores
        db_append.side_effect = OSError("pg down")
        await record_turn("alice", "room-1", "assistant", "Hi")
        r_append.assert_awaited_once()


class TestLoadRoomTurns:
    @pytest.mark.asyncio
    async def test_returns_spoken_turns_only(self, stores):
        """Only non-empty user/assistant turns are returned, order preserved."""
        _, r_hist, _ = stores
        r_hist.return_value = [
            {"role": "assistant", "content": "Welcome"},
            {"role": "system", "content": "ignored"},
            {"role": "user", "content": ""},
            {"role": "user", "content": "Tell me about light"},
        ]
        turns = await load_room_turns("room-1")
        assert [t["content"] for t in turns] == ["Welcome", "Tell me about light"]
        r_hist.assert_awaited_once_with("room-1")

    @pytest.mark.asyncio
    async def test_empty_room_returns_empty_list(self, stores):
        """A room with no live conversation yields []."""
        _, r_hist, _ = stores
        r_hist.return_value = []
        assert await load_room_turns("room-new") == []

    @pytest.mark.asyncio
    async def test_redis_failure_returns_empty_list(self, stores):
        """A Redis outage degrades to a fresh session instead of crashing the agent."""
        _, r_hist, _ = stores
        r_hist.side_effect = ConnectionError("redis down")
        assert await load_room_turns("room-1") == []
