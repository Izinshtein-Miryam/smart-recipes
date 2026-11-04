"""LLM client abstraction with OpenAI and mock implementations."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Protocol

from app.config import Settings


@dataclass(frozen=True)
class LLMResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int


class LLMClient(Protocol):
    model: str

    async def complete(self, system: str, user: str, max_tokens: int = 2048) -> LLMResult: ...

    def stream(self, system: str, user: str, max_tokens: int = 2048) -> AsyncIterator[str]: ...


class MockLLMClient:
    """Deterministic client for development and tests."""

    def __init__(self, response: str = "{}") -> None:
        self.model = "mock"
        self.response = response

    async def complete(self, system: str, user: str, max_tokens: int = 2048) -> LLMResult:
        return LLMResult(self.response, self.model, len(user) // 4, len(self.response) // 4)

    async def stream(self, system: str, user: str, max_tokens: int = 2048) -> AsyncIterator[str]:
        for i in range(0, len(self.response), 16):
            yield self.response[i : i + 16]


def _messages(system: str, user: str) -> list[dict[str, str]]:
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


class OpenAILLMClient:
    """OpenAI Chat Completions client. `client` may be injected (tests)."""

    def __init__(self, api_key: str, model: str, timeout: float, client: Any | None = None) -> None:
        if client is None:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=api_key, timeout=timeout)
        self.model = model
        self._client: Any = client

    async def complete(self, system: str, user: str, max_tokens: int = 2048) -> LLMResult:
        res = await self._client.chat.completions.create(
            model=self.model,
            max_completion_tokens=max_tokens,
            messages=_messages(system, user),
        )
        text = res.choices[0].message.content or ""
        usage = res.usage
        return LLMResult(
            text,
            self.model,
            usage.prompt_tokens if usage else 0,
            usage.completion_tokens if usage else 0,
        )

    async def stream(self, system: str, user: str, max_tokens: int = 2048) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=self.model,
            max_completion_tokens=max_tokens,
            messages=_messages(system, user),
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


def build_llm_client(settings: Settings) -> LLMClient:
    if settings.llm_provider == "openai":
        return OpenAILLMClient(
            settings.openai_api_key, settings.openai_model, settings.ai_timeout_seconds
        )
    return MockLLMClient()
