"""
Pydantic settings for the API service, loaded from environment variables.

Author: Pritam
Date: 2026-10-12
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings resolved from environment variables or a .env file.

    Attributes:
        LIVEKIT_API_KEY: API key for authenticating with the LiveKit server.
        LIVEKIT_API_SECRET: Corresponding API secret for token signing.
        LIVEKIT_URL: WebSocket URL of the LiveKit server.
        REDIS_URL: Connection URL for the Redis instance.
        DATABASE_URL: PostgreSQL connection URL for conversation persistence.
        AGENT_NAME: Name the agent worker registers under. Naming it disables
            LiveKit automatic dispatch, so only the API's explicit dispatch joins a room.
        JWT_SECRET: Secret used to sign user access tokens. Required, >= 32 chars.
        JWT_EXPIRE_HOURS: Lifetime of a user access token in hours.
        CORS_ORIGINS: Comma-separated browser origins allowed to call the API.
        TOKEN_RATE_LIMIT_PER_MINUTE: Max ``/token`` calls per user per minute.
    """

    LIVEKIT_API_KEY: str
    LIVEKIT_API_SECRET: str
    LIVEKIT_URL: str
    REDIS_URL: str = "redis://redis:6379"
    DATABASE_URL: str = "postgresql://eureka:eureka@postgres:5432/eureka"
    AGENT_NAME: str = "eureka-tutor"
    CORS_ORIGINS: str = "http://localhost:3000"
    TOKEN_RATE_LIMIT_PER_MINUTE: int = 5

    @field_validator("JWT_SECRET")
    @classmethod
    def _jwt_secret_strong(cls, v: str) -> str:
        """Refuse to start with a missing or guessable signing secret."""
        if len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters (try: openssl rand -hex 32)")
        if v.startswith("change-me"):
            raise ValueError("JWT_SECRET is still the .env.example placeholder (try: openssl rand -hex 32)")
        return v

    @property
    def cors_origins(self) -> list[str]:
        """Parsed ``CORS_ORIGINS`` list."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
    JWT_SECRET: str
    JWT_EXPIRE_HOURS: int = 24 * 7

    class Config:
        """Pydantic inner config for .env file loading."""

        env_file = ".env"


settings = Settings()
