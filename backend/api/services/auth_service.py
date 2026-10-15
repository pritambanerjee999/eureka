"""
Password hashing and access-token helpers for user authentication.

Passwords are hashed with scrypt (stdlib, memory-hard) using a per-user
random salt. Access tokens are HS256 JWTs whose ``sub`` claim is the username.

Author: Pritam
Date: 2026-10-12
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from config import settings

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hash a plaintext password with scrypt and a random salt.

    Args:
        password: The plaintext password.

    Returns:
        An encoded string ``scrypt$n$r$p$<salt_hex>$<hash_hex>``.
    """
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    """Check a plaintext password against an encoded scrypt hash.

    Args:
        password: The plaintext password to verify.
        encoded: The value previously returned by ``hash_password``.

    Returns:
        ``True`` if the password matches, ``False`` otherwise (including for
        malformed hashes).
    """
    try:
        scheme, n, r, p, salt_hex, hash_hex = encoded.split("$")
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode(),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), hash_hex)


def create_access_token(username: str) -> str:
    """Issue a signed JWT for an authenticated user.

    Args:
        username: The user's unique username, stored in the ``sub`` claim.

    Returns:
        An encoded JWT string valid for ``JWT_EXPIRE_HOURS``.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + timedelta(hours=settings.JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=_JWT_ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Validate a JWT and return its username.

    Args:
        token: The encoded JWT from the ``Authorization`` header.

    Returns:
        The username from the ``sub`` claim, or ``None`` if the token is
        invalid, expired, or missing the claim.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[_JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    sub = payload.get("sub")
    return sub if isinstance(sub, str) and sub else None
