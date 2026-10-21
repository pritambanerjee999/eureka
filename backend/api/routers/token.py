"""
Token router: issues LiveKit JWTs and initialises user sessions.

Author: Pritam
Date: 2026-10-12
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from livekit.api import CreateAgentDispatchRequest, DeleteRoomRequest, LiveKitAPI

from config import settings
from dependencies import get_current_user
from models.schemas import TokenRequest, TokenResponse
from services.session_service import create_session, hit_rate_limit, swap_active_room
from services.token_service import generate_token

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/token", response_model=TokenResponse)
async def get_token(
    request: TokenRequest,
    current_user: str = Depends(get_current_user),
) -> TokenResponse:
    """Issue a LiveKit token and create a Redis session for the participant.

    The participant identity is the authenticated username and the room name
    is always generated server-side. Guardrails: per-user rate limit, and one
    live session per user (the previous room is closed, ending its agent).
    Dispatches the agent worker to the room via the LiveKit API so it joins
    immediately and can start speaking.  Raises a 503 if the session store
    (Redis) is unreachable.

    Args:
        request: Optional, validated topic provided by the client.
        current_user: Authenticated username, used as the participant identity.

    Returns:
        A ``TokenResponse`` containing the signed JWT and connection details.

    Raises:
        HTTPException: 401 if unauthenticated, 429 if rate-limited, 503 if the
            session store is unavailable.
    """
    identity = current_user
    room_name = f"room-{uuid.uuid4().hex}"  # UUID4: 122 random bits, unguessable

    try:
        if await hit_rate_limit(identity, settings.TOKEN_RATE_LIMIT_PER_MINUTE):
            raise HTTPException(
                status_code=429, detail="Too many sessions started. Please wait a minute."
            )
        previous_room = await swap_active_room(identity, room_name)
        await create_session(
            room_name,
            identity,
            topic=request.topic,
            source="plan" if request.from_plan and request.topic else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Session store unavailable: {e}")

    token = generate_token(room_name, identity)

    # Dispatch the agent worker to this room so it joins and speaks first.
    # The worker is registered under AGENT_NAME, which opts it out of LiveKit's
    # automatic dispatch — otherwise every room would get a second agent.
    try:
        async with LiveKitAPI(
            url=settings.LIVEKIT_URL,
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET,
        ) as lk:
            if previous_room:
                try:
                    await lk.room.delete_room(DeleteRoomRequest(room=previous_room))
                    logger.info("Closed previous room %s for %s", previous_room, identity)
                except Exception as e:
                    logger.warning("Failed to close previous room %s: %s", previous_room, e)
            dispatch = await lk.agent_dispatch.create_dispatch(
                CreateAgentDispatchRequest(room=room_name, agent_name=settings.AGENT_NAME)
            )
            logger.info("Agent dispatched to room %s (id=%s)", room_name, dispatch.id)
    except Exception as e:
        logger.warning("Failed to dispatch agent to room %s: %s", room_name, e)

    return TokenResponse(
        token=token,
        room_name=room_name,
        identity=identity,
        livekit_url=settings.LIVEKIT_URL,
    )
