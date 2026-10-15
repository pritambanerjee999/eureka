"""
History router: exposes conversation history stored in PostgreSQL.

Author: Pritam
Date: 2026-10-12
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Path, status

from dependencies import get_current_user, require_identity
from models.schemas import NotesRequest, TitleRequest
from services.db import get_pool
from services.session_service import get_session

logger = logging.getLogger(__name__)

router = APIRouter()

# Server-generated room names only (8-hex legacy or 32-hex current).
_ROOM_NAME_PATTERN = r"^room-[0-9a-f]{8,32}$"


async def _owns_room(conn, identity: str, room_name: str) -> bool:
    """Whether ``room_name`` is one of ``identity``'s sessions.

    A live room is checked against its Redis session (written by ``/token``);
    an older one against the stored conversation.

    Args:
        conn: An acquired asyncpg connection.
        identity: The authenticated username.
        room_name: The room the notes belong to.

    Returns:
        True if the room belongs to ``identity``.
    """
    try:
        session = await get_session(room_name)
    except Exception as exc:
        logger.warning("Redis session lookup failed for %s: %s", room_name, exc)
        session = None
    if session is not None:
        return session.get("identity") == identity
    found = await conn.fetchval(
        "SELECT 1 FROM conversations WHERE identity = $1 AND room_name = $2 LIMIT 1",
        identity,
        room_name,
    )
    return bool(found)


@router.get("/history/{identity}")
async def get_history(identity: str, current_user: str = Depends(get_current_user)) -> dict:
    """Return all conversation messages for a given participant identity.

    Args:
        identity: The participant identity path parameter.
        current_user: Authenticated username; must match ``identity``.

    Raises:
        HTTPException: 401 if unauthenticated, 403 if ``identity`` is not the caller.

    Returns:
        A dict with keys ``identity``, ``messages`` (each with ``role``,
        ``content``, ``room_name`` and ``timestamp``) and ``titles`` (custom
        session names, keyed by room name).
    """
    require_identity(identity, current_user)
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT role, content, room_name, created_at
            FROM conversations
            WHERE identity = $1
            ORDER BY created_at ASC
            """,
            identity,
        )
        title_rows = await conn.fetch(
            "SELECT room_name, title FROM session_titles WHERE identity = $1",
            identity,
        )
    messages = [
        {
            "role": r["role"],
            "content": r["content"],
            "room_name": r["room_name"],
            "timestamp": r["created_at"].isoformat(),
        }
        for r in rows
    ]
    titles = {r["room_name"]: r["title"] for r in title_rows}
    return {"identity": identity, "messages": messages, "titles": titles}


@router.get("/notes/{identity}")
async def get_all_notes(identity: str, current_user: str = Depends(get_current_user)) -> dict:
    """Return all saved notes for a given participant identity.

    Args:
        identity: The participant identity path parameter.
        current_user: Authenticated username; must match ``identity``.

    Returns:
        A dict with key ``notes``, a list of ``{room_name, content, updated_at}``.
    """
    require_identity(identity, current_user)
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT room_name, content, updated_at
            FROM notes
            WHERE identity = $1
            ORDER BY updated_at DESC
            """,
            identity,
        )
    return {
        "identity": identity,
        "notes": [
            {
                "room_name": r["room_name"],
                "content": r["content"],
                "updated_at": r["updated_at"].isoformat(),
            }
            for r in rows
        ],
    }


@router.put("/notes/{identity}/{room_name}")
async def save_notes(
    identity: str,
    body: NotesRequest,
    room_name: str = Path(pattern=_ROOM_NAME_PATTERN),
    current_user: str = Depends(get_current_user),
) -> dict:
    """Upsert notes for a specific session.

    Args:
        identity: The participant identity path parameter.
        current_user: Authenticated username; must match ``identity``.
        room_name: The LiveKit room identifier.
        body: Validated notes body (string ``content``, size-capped).

    Raises:
        HTTPException: 403 if ``identity`` is not the caller, 404 if the room
            isn't one of the caller's sessions.

    Returns:
        A dict confirming the save operation.
    """
    content = body.content
    require_identity(identity, current_user)
    pool = await get_pool()
    async with pool.acquire() as conn:
        # 404 rather than 403 so the response doesn't reveal whether the room exists.
        if not await _owns_room(conn, identity, room_name):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        await conn.execute(
            """
            INSERT INTO notes (identity, room_name, content, updated_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (identity, room_name)
            DO UPDATE SET content = EXCLUDED.content, updated_at = NOW()
            """,
            identity,
            room_name,
            content,
        )
    return {"saved": True}


@router.put("/sessions/{identity}/{room_name}/title")
async def rename_session(
    identity: str,
    body: TitleRequest,
    room_name: str = Path(pattern=_ROOM_NAME_PATTERN),
    current_user: str = Depends(get_current_user),
) -> dict:
    """Rename one of the caller's sessions (an empty title resets it).

    Args:
        identity: The participant identity path parameter.
        body: Validated title (whitespace collapsed, at most 80 characters).
        room_name: The session's LiveKit room.
        current_user: Authenticated username; must match ``identity``.

    Raises:
        HTTPException: 403 if ``identity`` is not the caller, 404 if the room
            isn't one of the caller's sessions.

    Returns:
        ``{"room_name", "title"}``, where ``title`` is ``None`` after a reset.
    """
    require_identity(identity, current_user)
    pool = await get_pool()
    async with pool.acquire() as conn:
        if not await _owns_room(conn, identity, room_name):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        if not body.title:
            await conn.execute(
                "DELETE FROM session_titles WHERE identity = $1 AND room_name = $2",
                identity,
                room_name,
            )
            return {"room_name": room_name, "title": None}
        await conn.execute(
            """
            INSERT INTO session_titles (identity, room_name, title, updated_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (identity, room_name)
            DO UPDATE SET title = EXCLUDED.title, updated_at = NOW()
            """,
            identity,
            room_name,
            body.title,
        )
    return {"room_name": room_name, "title": body.title}
