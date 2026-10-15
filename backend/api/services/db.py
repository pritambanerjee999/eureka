"""
Shared asyncpg connection pool and schema bootstrap for the API service.

Author: Pritam
Date: 2026-10-12
"""

import asyncpg

from config import settings

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Return the shared asyncpg connection pool, creating it on first call.

    Ensures all required tables exist before any queries run.

    Returns:
        An asyncpg.Pool ready for use.
    """
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.DATABASE_URL, min_size=1, max_size=5
        )
        async with _pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id            BIGSERIAL PRIMARY KEY,
                    username      TEXT        NOT NULL UNIQUE,
                    password_hash TEXT        NOT NULL,
                    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
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
            await conn.execute("""
                ALTER TABLE conversations ADD COLUMN IF NOT EXISTS room_name TEXT
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    identity   TEXT        NOT NULL,
                    room_name  TEXT        NOT NULL,
                    content    TEXT        NOT NULL DEFAULT '',
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (identity, room_name)
                )
            """)
    return _pool
