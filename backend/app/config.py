"""
InsightSentinel Backend Configuration
"""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Environment
    environment: str = Field(default="development")

    # LLM Provider: "gemini" or "anthropic" (via Agent Maestro)
    llm_provider: str = Field(default="anthropic")

    # API Keys
    gemini_api_key: str = Field(default="")

    # Agent Maestro (for free Claude access via GitHub Copilot)
    agent_maestro_url: str = Field(default="http://localhost:23333/api/anthropic")
    claude_model_light: str = Field(default="claude-opus-4.5")
    claude_model_heavy: str = Field(default="claude-opus-4.5")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/insightsentinel"
    )
    database_echo: bool = Field(default=False)

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"]
    )

    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
