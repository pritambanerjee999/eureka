"""
Agent entrypoint: connects to a LiveKit room and runs the PhysicsTutorAgent.

Author: Pritam
Date: 2026-10-12
"""

import asyncio
import json
import logging

from dotenv import load_dotenv
from livekit.agents import AgentSession, JobContext, WorkerOptions, cli
from livekit.plugins import openai, silero

from agent import PhysicsTutorAgent, safe_topic
from config import settings
from services.conversation_service import load_room_turns, record_turn, turn_from_item
from services.pause_service import PauseController
from services.redis_service import (
    get_session_identity,
    get_session_source,
    get_session_topic,
)

load_dotenv()

# No basicConfig: the LiveKit CLI configures logging; a second root handler
# printed every line twice.
logger = logging.getLogger(__name__)


async def entrypoint(ctx: JobContext) -> None:
    """Connect to a LiveKit room, build the agent session, and persist transcripts.

    Reads the selected topic and identity from Redis, restores any live
    conversation already stored for this room (e.g. after a worker restart),
    and records every spoken turn via the conversation service.

    Args:
        ctx: The LiveKit job context carrying room and connection details.
    """
    await ctx.connect()
    logger.info("Agent connected to room: %s", ctx.room.name)

    # Read the topic and identity the student set before joining
    topic = safe_topic(await get_session_topic(ctx.room.name))
    identity = await get_session_identity(ctx.room.name)
    source = await get_session_source(ctx.room.name)
    prior_turns = await load_room_turns(ctx.room.name)
    logger.info(
        "Session topic=%s source=%s identity=%s prior_turns=%d",
        topic,
        source,
        identity,
        len(prior_turns),
    )

    session = AgentSession(
        # Cost guardrail: user_state becomes "away" after this much silence.
        user_away_timeout=settings.USER_AWAY_SECONDS,
        vad=silero.VAD.load(),
        stt=openai.STT(model="whisper-1"),
        llm=openai.LLM(model="gpt-4o"),
        tts=openai.TTS(voice="alloy"),
    )

    def _user_key() -> str:
        """Return the student's identity for history storage.

        Prefers the identity the API stored in Redis; falls back to the first
        remote participant, then the room name.

        Returns:
            A string key uniquely identifying the user for history storage.
        """
        if identity:
            return identity
        for participant_identity in ctx.room.remote_participants:
            return participant_identity
        return ctx.room.name

    @session.on("conversation_item_added")
    def on_conversation_item(ev) -> None:
        """Persist each committed user/assistant turn (Redis + PostgreSQL).

        Args:
            ev: ``ConversationItemAddedEvent`` carrying the new chat item.
        """
        turn = turn_from_item(ev.item)
        if turn:
            role, text = turn
            asyncio.create_task(record_turn(_user_key(), ctx.room.name, role, text))

    ending = False

    async def _end_session(reason: str, farewell: str) -> None:
        """Say a short goodbye, then close the room (disconnects the student too)."""
        nonlocal ending
        if ending:
            return
        ending = True
        logger.info("Ending session in %s: %s", ctx.room.name, reason)
        try:
            await session.say(farewell, allow_interruptions=False)
        except Exception as exc:
            logger.warning("Farewell failed: %s", exc)
        await ctx.delete_room()

    pauser = PauseController(
        session,
        _end_session,
        max_pause_seconds=settings.MAX_PAUSE_SECONDS,
        idle_seconds=settings.USER_AWAY_SECONDS,
    )

    @ctx.room.on("participant_attributes_changed")
    def on_attributes(changed: dict, participant) -> None:
        """The student's browser sets ``paused`` to pause/resume the session."""
        if identity is None or participant.identity == identity:
            pauser.handle_attributes(changed)

    @session.on("user_state_changed")
    def on_user_state(ev) -> None:
        """End idle sessions so an open tab doesn't keep a paid pipeline running."""
        if ev.new_state == "speaking":
            pauser.user_spoke()
        if ev.new_state == "away" and pauser.should_end_on_away():
            asyncio.create_task(
                _end_session(
                    "user away",
                    "It's gone quiet, so I'll end our session here. Come back anytime!",
                )
            )

    async def _session_time_limit() -> None:
        await asyncio.sleep(settings.MAX_SESSION_SECONDS)
        await _end_session(
            "max duration",
            "We've reached the session time limit. Great work today, start a new session anytime!",
        )

    limit_task = asyncio.create_task(_session_time_limit())
    ctx.add_shutdown_callback(lambda: _cancel(limit_task))
    ctx.add_shutdown_callback(_close_pauser(pauser))

    await session.start(
        room=ctx.room,
        agent=PhysicsTutorAgent(
            topic=topic,
            room_name=ctx.room.name,
            identity=identity,
            prior_turns=prior_turns,
            source=source,
        ),
    )


def _close_pauser(pauser: PauseController):
    """Build a shutdown callback that cancels the pause timers."""

    async def _close() -> None:
        pauser.close()

    return _close


async def _cancel(task: asyncio.Task) -> None:
    """Shutdown callback: stop the session time-limit timer."""
    task.cancel()


if __name__ == "__main__":
    # A named worker is excluded from LiveKit automatic dispatch; it only joins
    # rooms the API explicitly dispatches it to (one agent per room).
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, agent_name=settings.AGENT_NAME))
