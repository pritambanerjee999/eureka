"""
Shared FastAPI dependencies for request authentication.

Author: Pritam
Date: 2026-10-12
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.auth_service import decode_access_token

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Resolve the authenticated username from the Bearer token.

    Args:
        credentials: Parsed ``Authorization: Bearer <jwt>`` header, if present.

    Returns:
        The authenticated username (also used as the participant identity).

    Raises:
        HTTPException: 401 if the header is missing or the token is invalid.
    """
    username = decode_access_token(credentials.credentials) if credentials else None
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username


def require_identity(identity: str, current_user: str) -> None:
    """Ensure a path ``identity`` belongs to the authenticated user.

    Args:
        identity: The identity from the request path.
        current_user: The authenticated username.

    Raises:
        HTTPException: 403 if the identity belongs to someone else.
    """
    if identity != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
