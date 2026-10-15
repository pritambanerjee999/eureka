"""
Pydantic settings for the agent service, loaded from environment variables.

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
        OPENAI_API_KEY: API key for OpenAI STT, LLM, and TTS services.
        REDIS_URL: Connection URL for the Redis instance.
        DATABASE_URL: PostgreSQL connection URL for conversation persistence.
        AGENT_NAME: Name the agent worker registers under. Naming it disables
            LiveKit automatic dispatch, so only the API's explicit dispatch joins a room.
        MAX_SESSION_SECONDS: Hard cap on a session's length (cost guardrail).
        USER_AWAY_SECONDS: End the session after this long without the student speaking.
        MAX_PAUSE_SECONDS: End the session if it stays paused this long.
    """

    LIVEKIT_API_KEY: str
    LIVEKIT_API_SECRET: str
    LIVEKIT_URL: str
    OPENAI_API_KEY: str
    REDIS_URL: str = "redis://redis:6379"
    DATABASE_URL: str = "postgresql://eureka:eureka@postgres:5432/eureka"
    AGENT_NAME: str = "eureka-tutor"
    MAX_SESSION_SECONDS: int = 30 * 60
    USER_AWAY_SECONDS: float = 3 * 60
    MAX_PAUSE_SECONDS: float = 10 * 60

    class Config:
        """Pydantic inner config for .env file loading."""

        env_file = ".env"


settings = Settings()
