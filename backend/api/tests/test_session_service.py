"""
Unit tests for the session_service module.

Redis is mocked via unittest.mock so no real Redis instance is needed.

Author: Pritam
Date: 2026-10-12
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_redis_mock():
    """Return a fresh AsyncMock that mimics redis.asyncio client behaviour."""
    r = AsyncMock()
    r.hset = AsyncMock()
    r.expire = AsyncMock()
    r.sadd = AsyncMock()
    r.hgetall = AsyncMock()
    r.hset = AsyncMock()
    r.srem = AsyncMock()
    r.aclose = AsyncMock()
    return r


class TestCreateSession:
    @pytest.mark.asyncio
    async def test_create_session_stores_core_fields(self):
        """create_session should hset identity, status, and created_at."""
        r = _make_redis_mock()
        with patch("services.session_service.aioredis.from_url", return_value=r):
            from services.session_service import create_session

            result = await create_session("room-1", "user-1")

        mapping = r.hset.call_args.kwargs["mapping"]
        assert mapping["identity"] == "user-1"
        assert mapping["status"] == "active"
        assert "created_at" in mapping

    @pytest.mark.asyncio
    async def test_create_session_with_topic(self):
        """create_session should include topic in the hash when provided."""
        r = _make_redis_mock()
        with patch("services.session_service.aioredis.from_url", return_value=r):
            from services.session_service import create_session

            result = await create_session("room-2", "user-2", topic="Electromagnetism")

        mapping = r.hset.call_args.kwargs["mapping"]
        assert mapping.get("topic") == "Electromagnetism"

    @pytest.mark.asyncio
    async def test_create_session_without_topic_omits_field(self):
        """create_session should NOT include a topic key when none is given."""
        r = _make_redis_mock()
        with patch("services.session_service.aioredis.from_url", return_value=r):
            from services.session_service import create_session

            result = await create_session("room-3", "user-3")

        mapping = r.hset.call_args.kwargs["mapping"]
        assert "topic" not in mapping

    @pytest.mark.asyncio
    async def test_create_session_sets_expiry(self):
        """create_session should call expire with the SESSION_TTL value."""
        r = _make_redis_mock()
        with patch("services.session_service.aioredis.from_url", return_value=r):
            from services.session_service import create_session, SESSION_TTL

            await create_session("room-4", "user-4")

        r.expire.assert_called_once_with("session:room-4", SESSION_TTL)

    @pytest.mark.asyncio
    async def test_create_session_adds_to_active_rooms(self):
        """create_session should register the room in the active_rooms set."""
        r = _make_redis_mock()
        with patch("services.session_service.aioredis.from_url", return_value=r):
            from services.session_service import create_session

            await create_session("room-5", "user-5")

        r.sadd.assert_called_once_with("active_rooms", "room-5")

    @pytest.mark.asyncio
    async def test_create_session_closes_redis(self):
        """create_session should always close the Redis connection."""
        r = _make_redis_mock()
        with patch("services.session_service.aioredis.from_url", return_value=r):
            from services.session_service import create_session

            await create_session("room-6", "user-6")

        r.aclose.assert_called_once()


class TestGetSession:
    @pytest.mark.asyncio
    async def test_get_session_returns_decoded_dict(self):
        """get_session should decode bytes keys/values to strings."""
        r = _make_redis_mock()
        r.hgetall.return_value = {
            b"identity": b"user-7",
            b"status": b"active",
            b"created_at": b"2026-01-01T00:00:00+00:00",
        }
        with patch("services.session_service.aioredis.from_url", return_value=r):
            from services.session_service import get_session

            result = await get_session("room-7")

        assert result == {
            "identity": "user-7",
            "status": "active",
            "created_at": "2026-01-01T00:00:00+00:00",
        }

    @pytest.mark.asyncio
    async def test_get_session_returns_none_when_empty(self):
        """get_session should return None when the hash does not exist."""
        r = _make_redis_mock()
        r.hgetall.return_value = {}
        with patch("services.session_service.aioredis.from_url", return_value=r):
            from services.session_service import get_session

            result = await get_session("missing-room")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_session_closes_redis(self):
        """get_session should always close the Redis connection."""
        r = _make_redis_mock()
        r.hgetall.return_value = {}
        with patch("services.session_service.aioredis.from_url", return_value=r):
            from services.session_service import get_session

            await get_session("room-8")

        r.aclose.assert_called_once()


class TestEndSession:
    @pytest.mark.asyncio
    async def test_end_session_sets_status_ended(self):
        """end_session should hset status='ended' on the session key."""
        r = _make_redis_mock()
        with patch("services.session_service.aioredis.from_url", return_value=r):
            from services.session_service import end_session

            await end_session("room-9")

        r.hset.assert_called_once_with("session:room-9", "status", "ended")

    @pytest.mark.asyncio
    async def test_end_session_removes_from_active_rooms(self):
        """end_session should remove the room from the active_rooms set."""
        r = _make_redis_mock()
        with patch("services.session_service.aioredis.from_url", return_value=r):
            from services.session_service import end_session

            await end_session("room-10")

        r.srem.assert_called_once_with("active_rooms", "room-10")

    @pytest.mark.asyncio
    async def test_end_session_closes_redis(self):
        """end_session should always close the Redis connection."""
        r = _make_redis_mock()
        with patch("services.session_service.aioredis.from_url", return_value=r):
            from services.session_service import end_session

            await end_session("room-11")

        r.aclose.assert_called_once()


class TestRateLimit:
    @pytest.mark.asyncio
    async def test_first_call_sets_window_and_allows(self):
        r = _make_redis_mock()
        r.incr = AsyncMock(return_value=1)
        with patch("services.session_service.aioredis.from_url", return_value=r):
            from services.session_service import hit_rate_limit

            assert await hit_rate_limit("alice", 5) is False
        r.incr.assert_awaited_once_with("ratelimit:token:alice")
        r.expire.assert_awaited_once_with("ratelimit:token:alice", 60)
        r.aclose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_at_limit_allowed_over_limit_rejected(self):
        r = _make_redis_mock()
        with patch("services.session_service.aioredis.from_url", return_value=r):
            from services.session_service import hit_rate_limit

            r.incr = AsyncMock(return_value=5)
            assert await hit_rate_limit("alice", 5) is False
            r.incr = AsyncMock(return_value=6)
            assert await hit_rate_limit("alice", 5) is True
        r.expire.assert_not_called()

    @pytest.mark.asyncio
    async def test_redis_error_propagates_and_closes(self):
        r = _make_redis_mock()
        r.incr = AsyncMock(side_effect=ConnectionError("down"))
        with patch("services.session_service.aioredis.from_url", return_value=r):
            from services.session_service import hit_rate_limit

            with pytest.raises(ConnectionError):
                await hit_rate_limit("alice", 5)
        r.aclose.assert_awaited_once()


class TestSwapActiveRoom:
    @pytest.mark.asyncio
    async def test_returns_previous_room(self):
        r = _make_redis_mock()
        r.getset = AsyncMock(return_value=b"room-old")
        with patch("services.session_service.aioredis.from_url", return_value=r):
            from services.session_service import swap_active_room

            assert await swap_active_room("alice", "room-new") == "room-old"
        r.getset.assert_awaited_once_with("user_room:alice", "room-new")
        r.expire.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_previous_room(self):
        r = _make_redis_mock()
        r.getset = AsyncMock(return_value=None)
        with patch("services.session_service.aioredis.from_url", return_value=r):
            from services.session_service import swap_active_room

            assert await swap_active_room("alice", "room-new") is None

    @pytest.mark.asyncio
    async def test_same_room_is_not_reported_as_previous(self):
        r = _make_redis_mock()
        r.getset = AsyncMock(return_value="room-new")
        with patch("services.session_service.aioredis.from_url", return_value=r):
            from services.session_service import swap_active_room

            assert await swap_active_room("alice", "room-new") is None


class TestSessionSourceAndScope:
    @pytest.mark.asyncio
    async def test_create_session_stores_source(self):
        r = _make_redis_mock()
        with patch("services.session_service.aioredis.from_url", return_value=r):
            from services.session_service import create_session

            result = await create_session("room-3", "alice", topic="Momentum", source="plan")
        assert result["source"] == "plan"

    @pytest.mark.asyncio
    async def test_create_session_without_source_omits_field(self):
        r = _make_redis_mock()
        with patch("services.session_service.aioredis.from_url", return_value=r):
            from services.session_service import create_session

            result = await create_session("room-4", "alice", topic="Momentum")
        assert "source" not in result

    @pytest.mark.asyncio
    async def test_rate_limit_scope_selects_key(self):
        r = _make_redis_mock()
        r.incr = AsyncMock(return_value=1)
        with patch("services.session_service.aioredis.from_url", return_value=r):
            from services.session_service import hit_rate_limit

            await hit_rate_limit("alice", 10, scope="study_plan")
        r.incr.assert_awaited_once_with("ratelimit:study_plan:alice")
