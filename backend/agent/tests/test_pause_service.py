"""
Unit tests for PauseController (pause/resume of a tutoring session).

Author: Pritam
Date: 2026-10-14
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.pause_service import PauseController


def _make(user_state: str = "listening", max_pause: float = 60, idle: float = 60):
    session = MagicMock()
    session.user_state = user_state
    end_session = AsyncMock()
    return PauseController(session, end_session, max_pause, idle), session, end_session


class TestPauseResume:
    @pytest.mark.asyncio
    async def test_pause_interrupts_agent_and_blocks_idle_end(self):
        pauser, session, _ = _make()
        pauser.handle_attributes({"paused": "1"})
        assert pauser.paused
        session.interrupt.assert_called_once()
        assert pauser.should_end_on_away() is False
        pauser.close()

    @pytest.mark.asyncio
    async def test_resume_welcomes_student_back(self):
        pauser, session, _ = _make()
        pauser.handle_attributes({"paused": "1"})
        pauser.handle_attributes({"paused": "0"})
        assert not pauser.paused
        session.generate_reply.assert_called_once()
        assert "welcome them back" in session.generate_reply.call_args.kwargs["instructions"]
        assert pauser.should_end_on_away() is True
        pauser.close()

    @pytest.mark.asyncio
    async def test_repeated_events_are_idempotent(self):
        pauser, session, _ = _make()
        pauser.handle_attributes({"paused": "0"})  # resume without pause: no-op
        session.generate_reply.assert_not_called()
        pauser.handle_attributes({"paused": "1"})
        pauser.handle_attributes({"paused": "1"})
        session.interrupt.assert_called_once()
        pauser.close()

    @pytest.mark.asyncio
    async def test_unrelated_attributes_ignored(self):
        pauser, session, _ = _make()
        pauser.handle_attributes({"something": "1"})
        assert not pauser.paused
        session.interrupt.assert_not_called()


class TestPauseTimers:
    @pytest.mark.asyncio
    async def test_long_pause_ends_session(self):
        pauser, _, end_session = _make(max_pause=0.01)
        pauser.pause()
        await asyncio.sleep(0.05)
        end_session.assert_awaited_once()
        assert end_session.call_args.args[0] == "paused too long"

    @pytest.mark.asyncio
    async def test_resume_cancels_pause_limit(self):
        pauser, _, end_session = _make(max_pause=0.02)
        pauser.pause()
        pauser.resume()
        await asyncio.sleep(0.05)
        end_session.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_silence_after_resume_ends_session(self):
        pauser, _, end_session = _make(user_state="away", idle=0.01)
        pauser.pause()
        pauser.resume()
        await asyncio.sleep(0.05)
        end_session.assert_awaited_once()
        assert end_session.call_args.args[0] == "user away after resume"

    @pytest.mark.asyncio
    async def test_speaking_after_resume_cancels_idle_end(self):
        pauser, _, end_session = _make(user_state="away", idle=0.02)
        pauser.pause()
        pauser.resume()
        pauser.user_spoke()
        await asyncio.sleep(0.05)
        end_session.assert_not_awaited()
