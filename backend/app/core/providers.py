"""Process-wide AI providers exposed as FastAPI dependencies (overridable in tests)."""

from functools import lru_cache

from app.config import get_settings
from app.services.ai.client import LLMClient, build_llm_client
from app.services.embeddings.provider import EmbeddingProvider, build_embedding_provider
from app.services.images.provider import ImageProvider, build_image_provider
from app.services.limits import RateLimiter


@lru_cache
def get_llm_client() -> LLMClient:
    return build_llm_client(get_settings())


@lru_cache
def get_image_provider() -> ImageProvider:
    return build_image_provider(get_settings())


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    return build_embedding_provider(get_settings())


@lru_cache
def get_rate_limiter() -> RateLimiter:
    return RateLimiter()
