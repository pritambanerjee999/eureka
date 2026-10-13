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

from agent import PhysicsTutorAgent
from config import settings
from services.conversation_service import load_room_turns, record_turn, turn_from_item
from services.redis_service import get_session_identity, get_session_topic

load_dotenv()

logging.basicConfig(level=logging.INFO)
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
    topic = await get_session_topic(ctx.room.name)
    identity = await get_session_identity(ctx.room.name)
    prior_turns = await load_room_turns(ctx.room.name)
    logger.info(
        "Session topic=%s identity=%s prior_turns=%d", topic, identity, len(prior_turns)
    )

    session = AgentSession(
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

    await session.start(
        room=ctx.room,
        agent=PhysicsTutorAgent(
            topic=topic,
            room_name=ctx.room.name,
            identity=identity,
            prior_turns=prior_turns,
        ),
    )


if __name__ == "__main__":
    # A named worker is excluded from LiveKit automatic dispatch; it only joins
    # rooms the API explicitly dispatches it to (one agent per room).
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, agent_name=settings.AGENT_NAME))
