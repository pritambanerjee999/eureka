"""
Pydantic settings for the API service, loaded from environment variables.

Author: Pritam
Date: 2026-10-12
"""

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
        JWT_SECRET: Secret used to sign user access tokens. Override in production.
        JWT_EXPIRE_HOURS: Lifetime of a user access token in hours.
    """

    LIVEKIT_API_KEY: str
    LIVEKIT_API_SECRET: str
    LIVEKIT_URL: str
    REDIS_URL: str = "redis://redis:6379"
    DATABASE_URL: str = "postgresql://eureka:eureka@postgres:5432/eureka"
    AGENT_NAME: str = "eureka-tutor"
    JWT_SECRET: str = "dev-only-change-me"
    JWT_EXPIRE_HOURS: int = 24 * 7

    class Config:
        """Pydantic inner config for .env file loading."""

        env_file = ".env"


settings = Settings()
