"""
Unit tests for the agent db_service module.

asyncpg is mocked so no real PostgreSQL connection is made.

Author: Pritam
Date: 2026-10-12
"""

import datetime
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

import services.db_service as db_service


def _make_mock_conn():
    conn = AsyncMock()
    conn.execute = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    return conn


def _make_mock_pool(conn):
    @asynccontextmanager
    async def _acquire():
        yield conn

    pool = MagicMock()
    pool.acquire = _acquire
    return pool


@pytest.fixture(autouse=True)
def reset_pool():
    """Reset the module-level pool singleton before each test."""
    db_service._pool = None
    yield
    db_service._pool = None


@pytest.fixture()
def mock_pool_and_conn():
    """Patch asyncpg.create_pool and return (pool, conn)."""
    conn = _make_mock_conn()
    pool = _make_mock_pool(conn)

    with patch("services.db_service.asyncpg.create_pool", new_callable=AsyncMock, return_value=pool):
        yield pool, conn


class TestAppendMessage:
    @pytest.mark.asyncio
    async def test_append_message_inserts_with_correct_params(self, mock_pool_and_conn):
        """append_message should INSERT identity, room_name, role, content."""
        _, conn = mock_pool_and_conn

        await db_service.append_message("user-1", "user", "Hello world", room_name="room-1")

        conn.execute.assert_called()
        sql, *args = conn.execute.call_args[0]
        assert "INSERT INTO conversations" in sql
        assert "user-1" in args
        assert "room-1" in args
        assert "user" in args
        assert "Hello world" in args

    @pytest.mark.asyncio
    async def test_append_message_without_room_name_passes_none(self, mock_pool_and_conn):
        """append_message without room_name should pass None as the room_name param."""
        _, conn = mock_pool_and_conn

        await db_service.append_message("user-2", "assistant", "Great question!")

        _, *args = conn.execute.call_args[0]
        assert None in args


class TestGetHistory:
    @pytest.mark.asyncio
    async def test_get_history_returns_list_of_dicts(self, mock_pool_and_conn):
        """get_history should return dicts with role/content/room_name/timestamp."""
        _, conn = mock_pool_and_conn
        ts = datetime.datetime(2026, 10, 12, tzinfo=datetime.timezone.utc)

        row = MagicMock()
        row.__getitem__ = lambda self, key: {
            "role": "user",
            "content": "What is entropy?",
            "room_name": "room-3",
            "created_at": ts,
        }[key]
        conn.fetch.return_value = [row]

        result = await db_service.get_history("user-3")

        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "What is entropy?"
        assert result[0]["room_name"] == "room-3"
        assert "2026-10-12" in result[0]["timestamp"]

    @pytest.mark.asyncio
    async def test_get_history_empty(self, mock_pool_and_conn):
        """get_history should return an empty list when there are no rows."""
        _, conn = mock_pool_and_conn
        conn.fetch.return_value = []

        result = await db_service.get_history("user-empty")

        assert result == []


class TestSaveNotes:
    @pytest.mark.asyncio
    async def test_save_notes_executes_upsert(self, mock_pool_and_conn):
        """save_notes should execute an INSERT ... ON CONFLICT upsert."""
        _, conn = mock_pool_and_conn

        await db_service.save_notes("user-4", "room-4", "My notes here")

        conn.execute.assert_called()
        sql, *args = conn.execute.call_args[0]
        assert "INSERT INTO notes" in sql
        assert "ON CONFLICT" in sql
        assert "user-4" in args
        assert "room-4" in args
        assert "My notes here" in args


class TestGetNotes:
    @pytest.mark.asyncio
    async def test_get_notes_returns_content_when_row_exists(self, mock_pool_and_conn):
        """get_notes should return the content string when a row is found."""
        _, conn = mock_pool_and_conn
        row = MagicMock()
        row.__getitem__ = lambda self, key: {"content": "Energy is conserved"}[key]
        conn.fetchrow.return_value = row

        result = await db_service.get_notes("user-5", "room-5")

        assert result == "Energy is conserved"

    @pytest.mark.asyncio
    async def test_get_notes_returns_empty_string_when_no_row(self, mock_pool_and_conn):
        """get_notes should return '' when no notes row exists."""
        _, conn = mock_pool_and_conn
        conn.fetchrow.return_value = None

        result = await db_service.get_notes("user-6", "room-6")

        assert result == ""


class TestGetAllNotes:
    @pytest.mark.asyncio
    async def test_get_all_notes_returns_list(self, mock_pool_and_conn):
        """get_all_notes should return a list of dicts ordered by updated_at DESC."""
        _, conn = mock_pool_and_conn
        ts = datetime.datetime(2026, 10, 12, tzinfo=datetime.timezone.utc)

        row = MagicMock()
        row.__getitem__ = lambda self, key: {
            "room_name": "room-7",
            "content": "Momentum notes",
            "updated_at": ts,
        }[key]
        conn.fetch.return_value = [row]

        result = await db_service.get_all_notes("user-7")

        assert len(result) == 1
        assert result[0]["room_name"] == "room-7"
        assert result[0]["content"] == "Momentum notes"
        assert "2026-10-12" in result[0]["updated_at"]

        # Verify the SQL used ORDER BY updated_at DESC
        sql = conn.fetch.call_args[0][0]
        assert "ORDER BY updated_at DESC" in sql

    @pytest.mark.asyncio
    async def test_get_all_notes_empty(self, mock_pool_and_conn):
        """get_all_notes should return an empty list when there are no notes."""
        _, conn = mock_pool_and_conn
        conn.fetch.return_value = []

        result = await db_service.get_all_notes("user-none")

        assert result == []


class TestClearHistory:
    @pytest.mark.asyncio
    async def test_clear_history_executes_delete(self, mock_pool_and_conn):
        """clear_history should execute a DELETE WHERE identity=$1 statement."""
        _, conn = mock_pool_and_conn

        await db_service.clear_history("user-del")

        conn.execute.assert_called()
        sql, *args = conn.execute.call_args[0]
        assert "DELETE" in sql.upper()
        assert "conversations" in sql
        assert "user-del" in args


class TestInitSchema:
    @pytest.mark.asyncio
    async def test_init_schema_runs_multiple_statements(self, mock_pool_and_conn):
        """_init_schema should call execute at least 4 times (tables + index + alter)."""
        _, conn = mock_pool_and_conn
        conn.execute.reset_mock()

        await db_service._init_schema(conn)

        assert conn.execute.call_count >= 4

    @pytest.mark.asyncio
    async def test_init_schema_creates_conversations_table(self, mock_pool_and_conn):
        """_init_schema should CREATE the conversations table."""
        _, conn = mock_pool_and_conn
        conn.execute.reset_mock()

        await db_service._init_schema(conn)

        all_sqls = " ".join(str(c[0][0]) for c in conn.execute.call_args_list)
        assert "conversations" in all_sqls.lower()

    @pytest.mark.asyncio
    async def test_init_schema_creates_notes_table(self, mock_pool_and_conn):
        """_init_schema should CREATE the notes table."""
        _, conn = mock_pool_and_conn
        conn.execute.reset_mock()

        await db_service._init_schema(conn)

        all_sqls = " ".join(str(c[0][0]) for c in conn.execute.call_args_list)
        assert "notes" in all_sqls.lower()
