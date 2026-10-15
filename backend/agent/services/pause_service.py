"""
Pause/resume handling for a tutoring session.

The student pauses from the browser by setting the participant attribute
``paused`` to ``"1"`` (and muting their mic); resuming sets it back to ``"0"``.
While paused the agent stops talking and the idle timeout is suspended, but a
pause can't last forever: after ``max_pause_seconds`` the session ends so an
abandoned tab doesn't hold a room open.

Author: Pritam
Date: 2026-10-14
"""

import asyncio
import logging
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)

PAUSE_ATTRIBUTE = "paused"

EndSession = Callable[[str, str], Awaitable[None]]


class PauseController:
    """Tracks the paused state and the timers that bound it.

    Args:
        session: The ``AgentSession`` (needs ``interrupt``, ``generate_reply``, ``user_state``).
        end_session: Coroutine ``(reason, farewell)`` that says goodbye and closes the room.
        max_pause_seconds: Longest a pause may last before the session ends.
        idle_seconds: After resuming, end the session if the student stays silent this long.
    """

    def __init__(
        self,
        session,
        end_session: EndSession,
        max_pause_seconds: float,
        idle_seconds: float,
    ) -> None:
        self._session = session
        self._end_session = end_session
        self._max_pause = max_pause_seconds
        self._idle = idle_seconds
        self._pause_task: asyncio.Task | None = None
        self._idle_task: asyncio.Task | None = None
        self.paused = False

    def handle_attributes(self, changed: dict[str, str]) -> None:
        """React to a participant attribute change from the student's browser.

        Args:
            changed: The attributes that changed (``{"paused": "1" | "0"}``).
        """
        if PAUSE_ATTRIBUTE not in changed:
            return
        if changed[PAUSE_ATTRIBUTE] == "1":
            self.pause()
        else:
            self.resume()

    def pause(self) -> None:
        """Stop the agent mid-sentence and start the max-pause timer."""
        if self.paused:
            return
        self.paused = True
        logger.info("Session paused")
        _cancel(self._idle_task)
        try:
            self._session.interrupt()
        except Exception as exc:
            logger.warning("interrupt on pause failed: %s", exc)
        self._pause_task = asyncio.create_task(self._pause_limit())

    def resume(self) -> None:
        """Welcome the student back and re-arm the idle timeout."""
        if not self.paused:
            return
        self.paused = False
        logger.info("Session resumed")
        _cancel(self._pause_task)
        self._session.generate_reply(
            instructions=(
                "The student just un-paused the session. In one short sentence, welcome them back "
                "and remind them where you left off, then ask a question to get them talking."
            )
        )
        # The idle ("away") event already fired or was ignored while paused and
        # won't fire again until the student speaks, so time this stretch ourselves.
        if self._session.user_state == "away":
            self._idle_task = asyncio.create_task(self._idle_limit())

    def should_end_on_away(self) -> bool:
        """Whether the idle-timeout should end the session (not while paused)."""
        return not self.paused

    def user_spoke(self) -> None:
        """The student spoke: cancel the post-resume idle timer."""
        _cancel(self._idle_task)

    def close(self) -> None:
        """Cancel all timers (session shutdown)."""
        _cancel(self._pause_task)
        _cancel(self._idle_task)

    async def _pause_limit(self) -> None:
        await asyncio.sleep(self._max_pause)
        await self._end_session(
            "paused too long",
            "You've been paused for a while, so I'll end our session here. Come back anytime!",
        )

    async def _idle_limit(self) -> None:
        await asyncio.sleep(self._idle)
        await self._end_session(
            "user away after resume",
            "It's gone quiet, so I'll end our session here. Come back anytime!",
        )


def _cancel(task: asyncio.Task | None) -> None:
    if task and not task.done():
        task.cancel()
