"""Application settings, loaded from environment variables and `.env`."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./smart_recipes.db"
    jwt_secret: str = "dev-only-secret-change-me-in-dotenv-file"  # noqa: S105 - overridden via .env
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7
    bcrypt_rounds: int = 12
    cookie_name: str = "access_token"
    cookie_secure: bool = False
    cors_origins: list[str] = ["http://localhost:5173"]
    media_dir: Path = Path("./media")

    llm_provider: Literal["mock", "anthropic"] = "mock"
    anthropic_api_key: str = ""
    claude_model: str = "claude-opus-5-5"
    ai_timeout_seconds: float = 30.0

    image_provider: Literal["mock", "gemini"] = "mock"
    gemini_api_key: str = ""

    embedding_provider: Literal["mock", "sentence"] = "mock"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache
def get_settings() -> Settings:
    return Settings()
