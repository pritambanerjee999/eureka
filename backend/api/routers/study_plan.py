"""
Study plan router: suggests the learner's next topics from their past lessons.

Author: Pritam
Date: 2026-10-21
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from config import settings
from dependencies import get_current_user, require_identity
from services.session_service import hit_rate_limit
from services.study_plan_service import get_next_topics

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/study-plan/{identity}")
async def get_study_plan(identity: str, current_user: str = Depends(get_current_user)) -> dict:
    """Return three suggested next topics for the caller.

    Suggestions come from the learner's session headers only, and both the
    headers and the suggestions are cached in Redis for 24 hours.

    Args:
        identity: The participant identity path parameter.
        current_user: Authenticated username; must match ``identity``.

    Raises:
        HTTPException: 401 if unauthenticated, 403 if ``identity`` is not the
            caller, 429 if rate-limited, 503 if Redis, Postgres or the LLM fails.

    Returns:
        ``{"topics": [{"topic", "reason"}]}``; empty for a learner with no lessons yet.
    """
    require_identity(identity, current_user)
    try:
        if await hit_rate_limit(
            identity, settings.STUDY_PLAN_RATE_LIMIT_PER_MINUTE, scope="study_plan"
        ):
            raise HTTPException(status_code=429, detail="Too many requests. Please wait a minute.")
        topics = await get_next_topics(identity)
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Study plan failed for %s: %s", identity, e)
        raise HTTPException(status_code=503, detail="Study plan unavailable. Please try again.")
    return {"topics": topics}
