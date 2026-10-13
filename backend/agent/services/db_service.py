"""
Persistent conversation history and notes backed by PostgreSQL via asyncpg.

Author: Pritam
Date: 2026-10-12
"""

import asyncpg

from config import settings

_pool: asyncpg.Pool | None = None


async def _get_pool() -> asyncpg.Pool:
    """Return the shared asyncpg connection pool, creating it on first call.

    Initialises the database schema the first time the pool is created so
    all tables and indexes exist before any queries are executed.

    Returns:
        An asyncpg.Pool ready for use.
    """
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.DATABASE_URL, min_size=1, max_size=5
        )
        async with _pool.acquire() as conn:
            await _init_schema(conn)
    return _pool


async def _init_schema(conn: asyncpg.Connection) -> None:
    """Create all tables and indexes if they do not already exist.

    Uses ``IF NOT EXISTS`` and ``ADD COLUMN IF NOT EXISTS`` so this is safe
    to call against an existing database (idempotent migrations).

    Args:
        conn: An active asyncpg database connection.
    """
    # Core conversation history
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id         BIGSERIAL PRIMARY KEY,
            identity   TEXT        NOT NULL,
            room_name  TEXT,
            role       TEXT        NOT NULL,
            content    TEXT        NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_conv_identity
        ON conversations (identity, created_at)
    """)
    # Add room_name column to existing tables that were created before this migration
    await conn.execute("""
        ALTER TABLE conversations ADD COLUMN IF NOT EXISTS room_name TEXT
    """)

    # Per-session notes (one text blob per session, upserted on save)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            identity   TEXT        NOT NULL,
            room_name  TEXT        NOT NULL,
            content    TEXT        NOT NULL DEFAULT '',
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (identity, room_name)
        )
    """)


async def append_message(
    identity: str,
    role: str,
    content: str,
    room_name: str | None = None,
) -> None:
    """Insert a single conversation message into the database.

    Args:
        identity: The participant identity string used as the conversation key.
        role: The speaker role, e.g. ``"user"``, ``"assistant"``,
            ``"checkpoint"``, ``"level"``, or ``"session_start"``.
        content: The text content of the message.
        room_name: Optional LiveKit room identifier for the message.
    """
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO conversations (identity, room_name, role, content)
            VALUES ($1, $2, $3, $4)
            """,
            identity,
            room_name,
            role,
            content,
        )


async def get_history(identity: str, limit: int = 200) -> list[dict]:
    """Retrieve the conversation history for a given identity.

    Args:
        identity: The participant identity whose history is requested.
        limit: Maximum number of messages to return, ordered oldest-first.

    Returns:
        A list of dicts with keys ``role``, ``content``, ``room_name``, and
        ``timestamp`` (ISO-8601 string).
    """
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT role, content, room_name, created_at
            FROM conversations
            WHERE identity = $1
            ORDER BY created_at ASC
            LIMIT $2
            """,
            identity,
            limit,
        )
    return [
        {
            "role": r["role"],
            "content": r["content"],
            "room_name": r["room_name"],
            "timestamp": r["created_at"].isoformat(),
        }
        for r in rows
    ]


async def save_notes(identity: str, room_name: str, content: str) -> None:
    """Upsert session notes for the given identity and room.

    Args:
        identity: The participant identity string.
        room_name: The LiveKit room identifier for the session.
        content: The full notes text (overwrites any existing notes).
    """
    pool = await _get_pool()
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


async def get_notes(identity: str, room_name: str) -> str:
    """Retrieve notes for a specific session.

    Args:
        identity: The participant identity string.
        room_name: The LiveKit room identifier.

    Returns:
        The notes content string, or an empty string if none exist.
    """
    pool = await _get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT content FROM notes WHERE identity = $1 AND room_name = $2",
            identity,
            room_name,
        )
    return row["content"] if row else ""


async def get_all_notes(identity: str) -> list[dict]:
    """Retrieve all notes for a given identity, keyed by room.

    Args:
        identity: The participant identity string.

    Returns:
        A list of dicts with keys ``room_name``, ``content``, and
        ``updated_at`` (ISO-8601 string).
    """
    pool = await _get_pool()
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
    return [
        {
            "room_name": r["room_name"],
            "content": r["content"],
            "updated_at": r["updated_at"].isoformat(),
        }
        for r in rows
    ]


async def clear_history(identity: str) -> None:
    """Delete all conversation records for a given identity.

    Args:
        identity: The participant identity whose history should be erased.
    """
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM conversations WHERE identity = $1", identity
        )
