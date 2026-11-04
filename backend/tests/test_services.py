import asyncio
import io

import pytest
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import AICall, AIFeature
from app.services.ai.client import (
    ChatMessage,
    LLMResult,
    LLMUnavailableError,
    MockLLMClient,
    build_llm_client,
)
from app.services.ai.pricing import cost_usd
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

MESSAGES: list[ChatMessage] = [{"role": "user", "content": "lorem ipsum"}]


def test_ai_service_logs_successful_call(db: Session) -> None:
    service = AIService(MockLLMClient(['{"foo": "bar"}'], model="claude-opus-5-5"), db, None)
    result = asyncio.run(service.complete(AIFeature.SEARCH, system="s", messages=MESSAGES))
    assert result.text == '{"foo": "bar"}'
    call = db.scalars(select(AICall)).one()
    assert call.feature == AIFeature.SEARCH
    assert call.status == "ok"
    assert call.cost_usd > 0


def test_ai_service_logs_failed_call(db: Session) -> None:
    service = AIService(MockLLMClient(), db)
    with pytest.raises(LLMUnavailableError):
        asyncio.run(service.complete(AIFeature.CHAT, system="s", messages=MESSAGES))
    assert db.scalars(select(AICall)).one().status == "error"


def test_mock_client_script() -> None:
    client = MockLLMClient(["foo", RuntimeError("bar"), "baz"])

    async def collect() -> str:
        chunks = [c async for c in client.stream(system="s", messages=MESSAGES)]
        assert isinstance(chunks[-1], LLMResult)
        return "".join(c for c in chunks if isinstance(c, str))

    assert asyncio.run(collect()) == "foo"
    with pytest.raises(RuntimeError):
        asyncio.run(collect())
    assert asyncio.run(collect()) == "baz"
    assert asyncio.run(collect()) == "baz"  # last response repeats
    assert len(client.calls) == 4


def test_mock_client_callable() -> None:
    client = MockLLMClient(lambda system, messages: messages[-1]["content"].upper())

    async def collect() -> str:
        return "".join(
            [c async for c in client.stream(system="s", messages=MESSAGES) if isinstance(c, str)]
        )

    assert asyncio.run(collect()) == "LOREM IPSUM"


def test_cost_table() -> None:
    assert cost_usd("claude-opus-5-5", 1_000_000, 1_000_000) == 24.0
    assert cost_usd("unknown", 10, 10) == 0.0


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
