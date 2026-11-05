"""LLM client abstraction with OpenAI and mock implementations."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

from openai.types.chat import ChatCompletionMessageParam

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


class OpenAILLMClient:
    def __init__(self, api_key: str, model: str, timeout: float) -> None:
        from openai import AsyncOpenAI

        self.model = model
        self._client = AsyncOpenAI(api_key=api_key, timeout=timeout)

    @staticmethod
    def _messages(system: str, user: str) -> list[ChatCompletionMessageParam]:
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    async def complete(self, system: str, user: str, max_tokens: int = 2048) -> LLMResult:
        resp = await self._client.chat.completions.create(
            model=self.model,
            max_completion_tokens=max_tokens,
            messages=self._messages(system, user),
        )
        text = resp.choices[0].message.content or ""
        usage = resp.usage
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
            messages=self._messages(system, user),
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
