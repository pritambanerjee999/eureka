"""
Conversation handling: routes each spoken turn to the right stores.

Redis (``conversation:{room}``) is the live, per-room conversation state the
agent reads back on (re)join; PostgreSQL is the durable, per-user history the
learning-history UI reads. Writes go to both concurrently and a failure in one
store never blocks the other.

Author: Pritam
Date: 2026-10-12
"""

import asyncio
import logging

from services import db_service, redis_service

logger = logging.getLogger(__name__)

SPOKEN_ROLES = ("user", "assistant")


def turn_from_item(item) -> tuple[str, str] | None:
    """Extract ``(role, text)`` from a ``conversation_item_added`` event item.

    Args:
        item: A ``ChatMessage`` (or other conversation item, e.g. a handoff).

    Returns:
        The role and stripped text for non-empty user/assistant messages,
        otherwise ``None``.
    """
    role = getattr(item, "role", None)
    text = getattr(item, "text_content", None)
    if role not in SPOKEN_ROLES or not isinstance(text, str) or not text.strip():
        return None
    return role, text.strip()


async def record_turn(identity: str, room_name: str, role: str, content: str) -> None:
    """Persist one spoken turn to Redis (live state) and PostgreSQL (history).

    Args:
        identity: The student's identity (username); keys the durable history.
        room_name: The LiveKit room; keys the live Redis conversation.
        role: ``"user"`` or ``"assistant"``.
        content: The transcript text.
    """
    results = await asyncio.gather(
        redis_service.append_message(room_name, role, content),
        db_service.append_message(identity, role, content, room_name=room_name),
        return_exceptions=True,
    )
    for store, result in zip(("redis", "postgres"), results):
        if isinstance(result, Exception):
            logger.warning("record_turn: %s write failed for room %s: %s", store, room_name, result)


async def load_room_turns(room_name: str) -> list[dict]:
    """Return the live conversation for a room from Redis, oldest first.

    Used when an agent (re)joins a room that already has a conversation —
    e.g. after a worker crash and redispatch — so it resumes with context.

    Args:
        room_name: The LiveKit room identifier.

    Returns:
        A list of ``{"role", "content", ...}`` dicts for user/assistant turns,
        or an empty list if none exist or Redis is unavailable.
    """
    try:
        turns = await redis_service.get_history(room_name)
    except Exception as exc:
        logger.warning("load_room_turns: redis read failed for room %s: %s", room_name, exc)
        return []
    return [t for t in turns if t.get("role") in SPOKEN_ROLES and t.get("content")]
