"""
Session lifecycle management backed by Redis for the API service.

Author: Pritam
Date: 2026-10-12
"""

from datetime import datetime, timezone

import redis.asyncio as aioredis

from config import settings

SESSION_TTL = 7200  # 2 hours


async def create_session(
    room_name: str,
    identity: str,
    topic: str | None = None,
    source: str | None = None,
) -> dict:
    """Create a new active session entry in Redis for a room and participant.

    Stores a hash under ``session:<room_name>`` and registers the room in
    the ``active_rooms`` set.  The hash expires automatically after
    ``SESSION_TTL`` seconds.

    Args:
        room_name: The LiveKit room identifier.
        identity: The participant identity joining the room.
        topic: Optional topic key the student selected before joining.
        source: Where the topic came from; ``"plan"`` when picked from the
            study plan, so the agent starts teaching without a subtopic menu.

    Returns:
        A dict containing ``identity``, ``created_at``, ``status``, and
        optionally ``topic`` and ``source`` keys.
    """
    r = aioredis.from_url(settings.REDIS_URL)
    try:
        session_data: dict[str, str] = {
            "identity": identity,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "active",
        }
        if topic:
            session_data["topic"] = topic
        if source:
            session_data["source"] = source
        key = f"session:{room_name}"
        await r.hset(key, mapping=session_data)
        await r.expire(key, SESSION_TTL)
        await r.sadd("active_rooms", room_name)
        return session_data
    finally:
        await r.aclose()


async def get_session(room_name: str) -> dict | None:
    """Retrieve the session hash for a given room from Redis.

    Args:
        room_name: The LiveKit room identifier to look up.

    Returns:
        A dict of session fields decoded to strings, or ``None`` if no session
        exists for the given room.
    """
    r = aioredis.from_url(settings.REDIS_URL)
    try:
        data = await r.hgetall(f"session:{room_name}")
        if not data:
            return None
        return {k.decode(): v.decode() for k, v in data.items()}
    finally:
        await r.aclose()


async def end_session(room_name: str) -> None:
    """Mark a session as ended and remove it from the active rooms set.

    Args:
        room_name: The LiveKit room identifier whose session should be closed.
    """
    r = aioredis.from_url(settings.REDIS_URL)
    try:
        await r.hset(f"session:{room_name}", "status", "ended")
        await r.srem("active_rooms", room_name)
    finally:
        await r.aclose()


async def hit_rate_limit(
    identity: str, limit: int, window_seconds: int = 60, scope: str = "token"
) -> bool:
    """Count a call against a fixed-window per-user limit.

    Args:
        identity: The authenticated user.
        limit: Maximum calls allowed per window.
        window_seconds: Window length in seconds.
        scope: Which endpoint's counter to use (``"token"``, ``"study_plan"``).

    Returns:
        ``True`` if this call exceeds the limit and should be rejected.
    """
    r = aioredis.from_url(settings.REDIS_URL)
    try:
        key = f"ratelimit:{scope}:{identity}"
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, window_seconds)
        return count > limit
    finally:
        await r.aclose()


async def swap_active_room(identity: str, room_name: str) -> str | None:
    """Record ``room_name`` as the user's only active room.

    Enforces one live session per user: the caller ends the returned previous
    room so abandoned tabs or scripted calls don't keep paid agents running.

    Args:
        identity: The authenticated user.
        room_name: The newly created room.

    Returns:
        The previously active room name, or ``None``.
    """
    r = aioredis.from_url(settings.REDIS_URL)
    try:
        previous = await r.getset(f"user_room:{identity}", room_name)
        await r.expire(f"user_room:{identity}", SESSION_TTL)
        if previous is None:
            return None
        previous = previous.decode() if isinstance(previous, bytes) else previous
        return previous if previous != room_name else None
    finally:
        await r.aclose()
