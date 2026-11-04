"""LLM client abstraction with Anthropic and mock implementations."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

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


class AnthropicLLMClient:
    def __init__(self, api_key: str, model: str, timeout: float) -> None:
        from anthropic import AsyncAnthropic

        self.model = model
        self._client = AsyncAnthropic(api_key=api_key, timeout=timeout)

    async def complete(self, system: str, user: str, max_tokens: int = 2048) -> LLMResult:
        msg = await self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(block.text for block in msg.content if block.type == "text")
        return LLMResult(text, self.model, msg.usage.input_tokens, msg.usage.output_tokens)

    async def stream(self, system: str, user: str, max_tokens: int = 2048) -> AsyncIterator[str]:
        async with self._client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        ) as stream:
            async for text in stream.text_stream:
                yield text


def build_llm_client(settings: Settings) -> LLMClient:
    if settings.llm_provider == "anthropic":
        return AnthropicLLMClient(
            settings.anthropic_api_key, settings.claude_model, settings.ai_timeout_seconds
        )
    return MockLLMClient()
