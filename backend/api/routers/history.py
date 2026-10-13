"""
History router: exposes conversation history stored in PostgreSQL.

Author: Pritam
Date: 2026-10-12
"""

from fastapi import APIRouter, Depends

from dependencies import get_current_user, require_identity
from services.db import get_pool

router = APIRouter()


@router.get("/history/{identity}")
async def get_history(identity: str, current_user: str = Depends(get_current_user)) -> dict:
    """Return all conversation messages for a given participant identity.

    Args:
        identity: The participant identity path parameter.
        current_user: Authenticated username; must match ``identity``.

    Raises:
        HTTPException: 401 if unauthenticated, 403 if ``identity`` is not the caller.

    Returns:
        A dict with keys ``identity`` and ``messages``, where ``messages``
        includes ``role``, ``content``, ``room_name``, and ``timestamp``.
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
    messages = [
        {
            "role": r["role"],
            "content": r["content"],
            "room_name": r["room_name"],
            "timestamp": r["created_at"].isoformat(),
        }
        for r in rows
    ]
    return {"identity": identity, "messages": messages}


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
    room_name: str,
    body: dict,
    current_user: str = Depends(get_current_user),
) -> dict:
    """Upsert notes for a specific session.

    Args:
        identity: The participant identity path parameter.
        current_user: Authenticated username; must match ``identity``.
        room_name: The LiveKit room identifier.
        body: JSON body with a ``content`` key.

    Returns:
        A dict confirming the save operation.
    """
    content = body.get("content", "")
    require_identity(identity, current_user)
    pool = await get_pool()
    async with pool.acquire() as conn:
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
