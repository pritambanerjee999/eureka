"""
Unit tests for the agent redis_service module.

redis.asyncio is mocked so no real Redis instance is needed.

Author: Pritam
Date: 2026-10-12
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

import services.redis_service as redis_service


def _make_redis_mock():
    r = AsyncMock()
    r.hget = AsyncMock()
    r.rpush = AsyncMock()
    r.ltrim = AsyncMock()
    r.expire = AsyncMock()
    r.lrange = AsyncMock(return_value=[])
    r.delete = AsyncMock()
    r.aclose = AsyncMock()
    return r


class TestGetSessionTopic:
    @pytest.mark.asyncio
    async def test_returns_string_when_hget_returns_bytes(self):
        """get_session_topic should decode bytes to str."""
        r = _make_redis_mock()
        r.hget.return_value = b"Electromagnetism"
        with patch("services.redis_service.aioredis.from_url", return_value=r):
            result = await redis_service.get_session_topic("room-1")
        assert result == "Electromagnetism"

    @pytest.mark.asyncio
    async def test_returns_string_when_hget_returns_str(self):
        """get_session_topic should return a plain string as-is."""
        r = _make_redis_mock()
        r.hget.return_value = "Waves"
        with patch("services.redis_service.aioredis.from_url", return_value=r):
            result = await redis_service.get_session_topic("room-2")
        assert result == "Waves"

    @pytest.mark.asyncio
    async def test_returns_none_when_hget_returns_none(self):
        """get_session_topic should return None when no topic is stored."""
        r = _make_redis_mock()
        r.hget.return_value = None
        with patch("services.redis_service.aioredis.from_url", return_value=r):
            result = await redis_service.get_session_topic("room-3")
        assert result is None

    @pytest.mark.asyncio
    async def test_aclose_always_called(self):
        """get_session_topic should call r.aclose() even on the happy path."""
        r = _make_redis_mock()
        r.hget.return_value = b"Light"
        with patch("services.redis_service.aioredis.from_url", return_value=r):
            await redis_service.get_session_topic("room-4")
        r.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_aclose_called_on_exception(self):
        """get_session_topic should call r.aclose() even if hget raises."""
        r = _make_redis_mock()
        r.hget.side_effect = RuntimeError("Redis error")
        with patch("services.redis_service.aioredis.from_url", return_value=r):
            with pytest.raises(RuntimeError):
                await redis_service.get_session_topic("room-5")
        r.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_correct_key_used(self):
        """get_session_topic should look up 'session:<room_name>' / 'topic'."""
        r = _make_redis_mock()
        r.hget.return_value = None
        with patch("services.redis_service.aioredis.from_url", return_value=r):
            await redis_service.get_session_topic("my-room")
        r.hget.assert_called_once_with("session:my-room", "topic")


class TestAppendMessage:
    @pytest.mark.asyncio
    async def test_append_message_pushes_json(self):
        """append_message should rpush a JSON-encoded message."""
        import json
        r = _make_redis_mock()
        with patch("services.redis_service.aioredis.from_url", return_value=r):
            await redis_service.append_message("room-6", "user", "Hello")
        r.rpush.assert_called_once()
        key, payload = r.rpush.call_args[0]
        assert key == "conversation:room-6"
        decoded = json.loads(payload)
        assert decoded["role"] == "user"
        assert decoded["content"] == "Hello"

    @pytest.mark.asyncio
    async def test_append_message_trims_and_expires(self):
        """append_message should call ltrim and expire after rpush."""
        r = _make_redis_mock()
        with patch("services.redis_service.aioredis.from_url", return_value=r):
            await redis_service.append_message("room-7", "assistant", "Answer")
        r.ltrim.assert_called_once()
        r.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_append_message_closes_redis(self):
        """append_message should always close the Redis connection."""
        r = _make_redis_mock()
        with patch("services.redis_service.aioredis.from_url", return_value=r):
            await redis_service.append_message("room-8", "user", "Bye")
        r.aclose.assert_called_once()


class TestGetHistory:
    @pytest.mark.asyncio
    async def test_get_history_returns_decoded_messages(self):
        """get_history should deserialise JSON messages from Redis."""
        import json
        r = _make_redis_mock()
        msg = json.dumps({"role": "user", "content": "hi", "timestamp": "2026-01-01"}).encode()
        r.lrange.return_value = [msg]
        with patch("services.redis_service.aioredis.from_url", return_value=r):
            result = await redis_service.get_history("room-9")
        assert len(result) == 1
        assert result[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_get_history_empty(self):
        """get_history should return an empty list when no messages exist."""
        r = _make_redis_mock()
        r.lrange.return_value = []
        with patch("services.redis_service.aioredis.from_url", return_value=r):
            result = await redis_service.get_history("room-empty")
        assert result == []


class TestClearHistory:
    @pytest.mark.asyncio
    async def test_clear_history_deletes_key(self):
        """clear_history should delete the conversation key."""
        r = _make_redis_mock()
        with patch("services.redis_service.aioredis.from_url", return_value=r):
            await redis_service.clear_history("room-10")
        r.delete.assert_called_once_with("conversation:room-10")
