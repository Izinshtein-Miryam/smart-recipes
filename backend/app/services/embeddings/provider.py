"""Local embedding provider abstraction + cosine similarity helpers."""

import hashlib
import math
import struct
from typing import Protocol

from app.config import Settings


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]: ...


class MockEmbeddingProvider:
    """Deterministic hash-based vectors; good enough for tests."""

    dim = 32

    def embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        return [b / 255 for b in digest[: self.dim]]


def to_blob(vector: list[float]) -> bytes:
    return struct.pack(f"{len(vector)}f", *vector)


def from_blob(blob: bytes) -> list[float]:
    return list(struct.unpack(f"{len(blob) // 4}f", blob))


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider == "sentence":
        from app.services.embeddings.sentence import SentenceEmbeddingProvider

        return SentenceEmbeddingProvider(settings.embedding_model)
    if settings.embedding_provider == "openai":
        from app.services.embeddings.openai_provider import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider(
            settings.openai_api_key,
            settings.openai_embedding_model,
            settings.ai_timeout_seconds,
        )
    return MockEmbeddingProvider()
