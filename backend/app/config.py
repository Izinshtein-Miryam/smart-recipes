"""Application settings, loaded from environment variables and `.env`."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://recipes:recipes@localhost:5432/recipes"
    cors_origins: list[str] = ["http://localhost:5173"]
    storage_dir: Path = Path("./storage")

    # OpenAI - the key lives on the server only; the client never talks to OpenAI.
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    ai_timeout_seconds: float = 30.0

    # Single admin: one password (stored as a bcrypt hash) and a JWT signing secret.
    admin_password_hash: str = ""
    jwt_secret: str = "dev-only-secret-change-me"  # noqa: S105 - overridden via env
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 12

    # Submission flood protection (POST /recipes only; this is not an AI usage limit).
    max_submissions_per_day: int = 5
    max_image_bytes: int = 5 * 1024 * 1024
    rejected_image_retention_days: int = 7
    chat_message_max_chars: int = 500


@lru_cache
def get_settings() -> Settings:
    return Settings()
