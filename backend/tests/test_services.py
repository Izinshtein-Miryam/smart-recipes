import asyncio
import base64
import io
from types import SimpleNamespace
from typing import Any

import pytest
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import AICall, AIFeature
from app.services.ai.client import LLMResult, MockLLMClient, OpenAILLMClient, build_llm_client
from app.services.ai.service import AIService
from app.services.embeddings.openai_provider import OpenAIEmbeddingProvider
from app.services.embeddings.provider import (
    MockEmbeddingProvider,
    build_embedding_provider,
    cosine,
    from_blob,
    to_blob,
)
from app.services.images.openai_provider import OpenAIImageProvider
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


# --- OpenAI providers, exercised against an in-memory fake SDK client ---


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, format="PNG")
    return buf.getvalue()


class _FakeStream:
    def __init__(self, parts: list[str | None]) -> None:
        self._chunks = [
            SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=p))])
            for p in parts
        ] + [SimpleNamespace(choices=[])]

    def __aiter__(self) -> "_FakeStream":
        return self

    async def __anext__(self) -> Any:
        if not self._chunks:
            raise StopAsyncIteration
        return self._chunks.pop(0)


class _FakeCompletions:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if kwargs.get("stream"):
            return _FakeStream(["lorem ", None, "ipsum"])
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="foo"))],
            usage=SimpleNamespace(prompt_tokens=7, completion_tokens=3),
        )


class _FakeImages:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def _result(self, prompt: str) -> Any:
        self.prompts.append(prompt)
        return SimpleNamespace(data=[SimpleNamespace(b64_json=base64.b64encode(_png_bytes()))])

    async def generate(self, **kwargs: Any) -> Any:
        return self._result(kwargs["prompt"])

    async def edit(self, **kwargs: Any) -> Any:
        return self._result(kwargs["prompt"])


def test_openai_llm_client_complete_and_stream() -> None:
    completions = _FakeCompletions()
    fake = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    client = OpenAILLMClient("key", "foo-model", 30, client=fake)

    result = asyncio.run(client.complete("system", "user", max_tokens=100))
    assert result == LLMResult("foo", "foo-model", 7, 3)
    call = completions.calls[0]
    assert call["max_completion_tokens"] == 100
    assert call["messages"][0] == {"role": "system", "content": "system"}

    async def collect() -> str:
        return "".join([chunk async for chunk in client.stream("s", "u")])

    assert asyncio.run(collect()) == "lorem ipsum"


def test_openai_image_provider_adds_system_prompt_and_returns_webp() -> None:
    images = _FakeImages()
    provider = OpenAIImageProvider("key", "bar-model", 60, client=SimpleNamespace(images=images))

    generated = asyncio.run(provider.generate("foo"))
    edited = asyncio.run(provider.edit(_png_bytes(), "bar"))
    assert Image.open(io.BytesIO(generated)).format == "WEBP"
    assert Image.open(io.BytesIO(edited)).format == "WEBP"
    assert all(p.startswith(IMAGE_SYSTEM_PROMPT) for p in images.prompts)


def test_openai_embedding_provider() -> None:
    embeddings = SimpleNamespace(
        create=lambda **kwargs: SimpleNamespace(data=[SimpleNamespace(embedding=[1, 0.5])])
    )
    provider = OpenAIEmbeddingProvider(
        "key", "baz-model", 30, client=SimpleNamespace(embeddings=embeddings)
    )
    assert provider.embed("foo") == [1.0, 0.5]


def test_factories_build_openai_providers() -> None:
    settings = Settings(
        llm_provider="openai",
        image_provider="openai",
        embedding_provider="openai",
        openai_api_key="sk-test",
    )
    assert isinstance(build_llm_client(settings), OpenAILLMClient)
    assert isinstance(build_image_provider(settings), OpenAIImageProvider)
    assert isinstance(build_embedding_provider(settings), OpenAIEmbeddingProvider)
