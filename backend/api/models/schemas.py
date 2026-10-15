"""
Pydantic request and response schemas for the Eureka API.

Author: Pritam
Date: 2026-10-12
"""

import re

from pydantic import BaseModel, Field, field_validator

_USERNAME_RE = re.compile(r"^[a-z0-9_-]{3,32}$")

# Topic titles are short menu labels ("Why do things fall?", "E=mc²"). Anything
# longer or with other punctuation/newlines is rejected before it can reach the
# agent's LLM instructions.
TOPIC_MAX_LEN = 80
_TOPIC_RE = re.compile(r"^[\w &'?=²\-]+$")

NOTES_MAX_LEN = 20_000


class TokenRequest(BaseModel):
    """Request body for the ``/token`` endpoint.

    The room name is always generated server-side so a client can never
    request a token for someone else's room.

    Attributes:
        topic: Optional topic key selected by the user (e.g. ``"Light"``);
            ``"__open__"`` means free-form chat, ``"__assess__"`` triggers the
            level-calibration flow.
    """

    topic: str | None = Field(default=None, max_length=TOPIC_MAX_LEN)

    @field_validator("topic")
    @classmethod
    def _validate_topic(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v or not _TOPIC_RE.match(v):
            raise ValueError("Invalid topic")
        return v


class TokenResponse(BaseModel):
    """Response body returned by the ``/token`` endpoint.

    Attributes:
        token: A signed LiveKit JWT granting room access.
        room_name: The server-generated room name.
        identity: The participant identity (the authenticated username).
        livekit_url: The LiveKit server WebSocket URL the client should connect to.
    """

    token: str
    room_name: str
    identity: str
    livekit_url: str


class RegisterRequest(BaseModel):
    """Request body for ``POST /auth/register``.

    Attributes:
        username: 3–32 chars of lowercase letters, digits, ``_`` or ``-``.
            Input is trimmed and lowercased before validation. Doubles as the
            LiveKit participant identity, so the ``user-`` prefix (used by
            legacy anonymous identities) is reserved.
        password: Plaintext password, 8–128 characters.
    """

    username: str
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def _validate_username(cls, v: str) -> str:
        v = v.strip().lower()
        if not _USERNAME_RE.match(v):
            raise ValueError(
                "Username must be 3-32 characters: letters, digits, '_' or '-'"
            )
        if v.startswith("user-"):
            raise ValueError("Usernames starting with 'user-' are reserved")
        return v


class LoginRequest(BaseModel):
    """Request body for ``POST /auth/login``.

    Attributes:
        username: The account username (case-insensitive).
        password: The plaintext password.
    """

    username: str = Field(max_length=64)
    password: str = Field(max_length=128)


class AuthResponse(BaseModel):
    """Response body for successful register/login.

    Attributes:
        access_token: Signed JWT to send as ``Authorization: Bearer <token>``.
        token_type: Always ``"bearer"``.
        username: The authenticated username.
    """

    access_token: str
    token_type: str = "bearer"
    username: str


class UserResponse(BaseModel):
    """Response body for ``GET /auth/me``.

    Attributes:
        username: The authenticated username.
    """

    username: str


class NotesRequest(BaseModel):
    """Request body for ``PUT /notes/{identity}/{room_name}``.

    Attributes:
        content: The notes text, at most ``NOTES_MAX_LEN`` characters.
    """

    content: str = Field(default="", max_length=NOTES_MAX_LEN)
