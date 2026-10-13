"""
LiveKit JWT generation for granting room access to participants.

Author: Pritam
Date: 2026-10-12
"""

from datetime import timedelta

from livekit.api import AccessToken, VideoGrants

from config import settings


def generate_token(room_name: str, identity: str) -> str:
    """Generate a signed LiveKit JWT granting audio publish/subscribe access.

    The token is valid for 2 hours and scoped to the specified room and
    identity with both publish and subscribe permissions.

    Args:
        room_name: The LiveKit room the token grants access to.
        identity: The participant identity embedded in the token claims.

    Returns:
        A signed JWT string suitable for passing to the LiveKit client SDK.
    """
    token = (
        AccessToken(
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET,
        )
        .with_identity(identity)
        .with_name(identity)
        .with_ttl(timedelta(hours=2))
        .with_grants(
            VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
            )
        )
    )
    return token.to_jwt()
