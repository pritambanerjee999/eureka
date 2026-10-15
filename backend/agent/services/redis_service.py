"""
Redis access for the agent: session metadata written by the API
(``session:{room}``) and the live per-room conversation
(``conversation:{room}``, bounded list with a 24-hour TTL).

Author: Pritam
Date: 2026-10-12
"""

import json
from datetime import datetime, timezone

import redis.asyncio as aioredis

from config import settings

CONVERSATION_TTL = 86400  # 24 hours — survives browser refresh
MAX_HISTORY = 200


async def get_session_identity(room_name: str) -> str | None:
    """Retrieve the user identity stored when the API issued the token.

    Args:
        room_name: The LiveKit room identifier.

    Returns:
        The identity string, or ``None`` if the session key has expired.
    """
    r = aioredis.from_url(settings.REDIS_URL)
    try:
        raw = await r.hget(f"session:{room_name}", "identity")
        if raw is None:
            return None
        return raw.decode() if isinstance(raw, bytes) else raw
    finally:
        await r.aclose()


async def get_session_topic(room_name: str) -> str | None:
    """Retrieve the topic the student selected before joining the room.

    Reads the ``topic`` field from the ``session:<room_name>`` Redis hash
    written by the API at token-issue time.

    Args:
        room_name: The LiveKit room identifier.

    Returns:
        The topic string (e.g. ``"Light"``), or ``None`` if no topic was set
        or the session key has expired.
    """
    r = aioredis.from_url(settings.REDIS_URL)
    try:
        raw = await r.hget(f"session:{room_name}", "topic")
        if raw is None:
            return None
        return raw.decode() if isinstance(raw, bytes) else raw
    finally:
        await r.aclose()


async def append_message(room_name: str, role: str, content: str) -> None:
    """Append a message to the Redis conversation list for the given room.

    Keeps the list bounded to ``MAX_HISTORY`` entries and resets the TTL on
    every write so active conversations do not expire mid-session.

    Args:
        room_name: The LiveKit room name used as part of the Redis key.
        role: The speaker role, e.g. ``"user"`` or ``"assistant"``.
        content: The text content of the message.
    """
    r = aioredis.from_url(settings.REDIS_URL)
    try:
        key = f"conversation:{room_name}"
        message = json.dumps(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        await r.rpush(key, message)
        # Keep the list bounded to prevent unbounded memory growth
        await r.ltrim(key, -MAX_HISTORY, -1)
        await r.expire(key, CONVERSATION_TTL)
    finally:
        await r.aclose()


async def get_history(room_name: str) -> list[dict]:
    """Retrieve all cached messages for the given room.

    Args:
        room_name: The LiveKit room name whose conversation history is needed.

    Returns:
        A list of message dicts, each containing ``role``, ``content``, and
        ``timestamp`` keys, in insertion order.
    """
    r = aioredis.from_url(settings.REDIS_URL)
    try:
        key = f"conversation:{room_name}"
        raw = await r.lrange(key, 0, -1)
        return [json.loads(m) for m in raw]
    finally:
        await r.aclose()


async def clear_history(room_name: str) -> None:
    """Delete the conversation history key for the given room.

    Args:
        room_name: The LiveKit room name whose cached history should be removed.
    """
    r = aioredis.from_url(settings.REDIS_URL)
    try:
        await r.delete(f"conversation:{room_name}")
    finally:
        await r.aclose()
