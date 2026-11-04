import asyncio
import io

import pytest
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import AICall, AIFeature
from app.services.ai.client import LLMResult, MockLLMClient, build_llm_client
from app.services.ai.service import AIService
from app.services.embeddings.provider import (
    MockEmbeddingProvider,
    build_embedding_provider,
    cosine,
    from_blob,
    to_blob,
)
from app.services.images.provider import (
    IMAGE_SYSTEM_PROMPT,
    MockImageProvider,
    build_image_provider,
)


def test_ai_service_logs_successful_call(db: Session) -> None:
    service = AIService(MockLLMClient('{"foo": "bar"}'), db)
    result = asyncio.run(service.complete(AIFeature.SEARCH, "system", "lorem ipsum"))
    assert result.text == '{"foo": "bar"}'
    call = db.scalars(select(AICall)).one()
    assert call.feature == AIFeature.SEARCH
    assert call.status == "ok"


class _FailingClient(MockLLMClient):
    async def complete(self, system: str, user: str, max_tokens: int = 2048) -> LLMResult:
        raise TimeoutError


def test_ai_service_logs_failed_call(db: Session) -> None:
    service = AIService(_FailingClient(), db)
    with pytest.raises(TimeoutError):
        asyncio.run(service.complete(AIFeature.CHAT, "s", "u"))
    assert db.scalars(select(AICall)).one().status == "error"


def test_mock_stream_yields_full_response() -> None:
    client = MockLLMClient("lorem ipsum dolor sit amet consectetur")

    async def collect() -> str:
        return "".join([chunk async for chunk in client.stream("s", "u")])

    assert asyncio.run(collect()) == client.response


def test_mock_image_provider_includes_system_prompt() -> None:
    provider = MockImageProvider()
    data = asyncio.run(provider.generate("foo"))
    assert IMAGE_SYSTEM_PROMPT in (provider.last_prompt or "")
    assert Image.open(io.BytesIO(data)).format == "WEBP"

    png = io.BytesIO()
    Image.new("RGB", (10, 10)).save(png, format="PNG")
    edited = asyncio.run(provider.edit(png.getvalue(), "bar"))
    assert Image.open(io.BytesIO(edited)).format == "WEBP"


def test_embeddings_roundtrip_and_similarity() -> None:
    provider = MockEmbeddingProvider()
    vec = provider.embed("foo")
    assert from_blob(to_blob(vec)) == pytest.approx(vec)
    assert cosine(vec, vec) == pytest.approx(1.0)
    assert cosine([0.0], [0.0]) == 0.0


def test_factories_default_to_mock() -> None:
    settings = Settings()
    assert isinstance(build_llm_client(settings), MockLLMClient)
    assert isinstance(build_image_provider(settings), MockImageProvider)
    assert isinstance(build_embedding_provider(settings), MockEmbeddingProvider)
