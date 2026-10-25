"""The single typed settings object. Values come from env vars / `.env`."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DOCS_COPILOT_", env_file=".env", extra="ignore")

    env: str = "dev"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://docs:docs@localhost:5432/docs_copilot"
    redis_url: str = "redis://localhost:6379/0"

    # Provider keys use their conventional names (no prefix).
    anthropic_api_key: SecretStr | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    voyage_api_key: SecretStr | None = Field(default=None, alias="VOYAGE_API_KEY")

    embedding_model: str = "voyage-3.5-lite"
    embedding_dim: int = 1024
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    chat_model_fast: str = "claude-haiku-5-5"
    chat_model_strong: str = "claude-sonnet-5-5"
    judge_model: str = "claude-opus-5-5"


@lru_cache
def get_settings() -> Settings:
    return Settings()
