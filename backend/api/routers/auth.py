"""
Auth router: user registration, login, and current-user lookup.

Author: Pritam
Date: 2026-10-12
"""

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from dependencies import get_current_user
from models.schemas import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from services.auth_service import create_access_token, hash_password, verify_password
from services.db import get_pool

router = APIRouter(prefix="/auth")


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest) -> AuthResponse:
    """Create a new user account and return an access token.

    Args:
        request: Desired username and password (validated by the schema).

    Returns:
        An ``AuthResponse`` with a signed access token and the username.

    Raises:
        HTTPException: 409 if the username is already taken.
    """
    pool = await get_pool()
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO users (username, password_hash) VALUES ($1, $2)",
                request.username,
                hash_password(request.password),
            )
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")
    return AuthResponse(access_token=create_access_token(request.username), username=request.username)


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest) -> AuthResponse:
    """Verify credentials and return an access token.

    Args:
        request: Username and password.

    Returns:
        An ``AuthResponse`` with a signed access token and the username.

    Raises:
        HTTPException: 401 if the username does not exist or the password is wrong.
    """
    username = request.username.strip().lower()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT username, password_hash FROM users WHERE username = $1", username
        )
    if row is None or not verify_password(request.password, row["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    return AuthResponse(access_token=create_access_token(row["username"]), username=row["username"])


@router.get("/me", response_model=UserResponse)
async def me(current_user: str = Depends(get_current_user)) -> UserResponse:
    """Return the authenticated user.

    Args:
        current_user: Username resolved from the Bearer token.

    Returns:
        A ``UserResponse`` with the username.
    """
    return UserResponse(username=current_user)
