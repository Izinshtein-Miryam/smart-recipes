"""LLM client abstraction. The real implementation lives in `anthropic_client.py`."""

from collections.abc import AsyncIterator, Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, TypedDict

from app.config import Settings

Effort = Literal["low", "medium", "high"]
JsonSchema = dict[str, Any]


class ChatMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class LLMResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int


class LLMError(Exception):
    """Base error for LLM calls. The message is safe to show to users."""


class LLMUnavailableError(LLMError):
    """The provider is not configured, unreachable, timed out or rate limited."""


class LLMRefusalError(LLMError):
    """The model declined the request."""


class LLMClient(Protocol):
    model: str

    def stream(
        self,
        *,
        system: str,
        messages: Sequence[ChatMessage],
        json_schema: JsonSchema | None = None,
        effort: Effort = "low",
        max_tokens: int = 4000,
    ) -> AsyncIterator[str | LLMResult]:
        """Yield text chunks, then exactly one final `LLMResult`."""
        ...


Responder = Callable[[str, Sequence[ChatMessage]], str]


@dataclass
class MockLLMClient:
    """Scripted client for tests and for running without an API key.

    `responses` are returned in order (the last one repeats). With no responses every call
    raises `LLMUnavailableError`, so features fall back exactly as when the API is down.
    """

    responses: list[str | Exception] | Responder = field(default_factory=list)
    model: str = "mock"
    calls: list[dict[str, Any]] = field(default_factory=list)

    def _next(self, system: str, messages: Sequence[ChatMessage]) -> str:
        if callable(self.responses):
            return self.responses(system, messages)
        if not self.responses:
            raise LLMUnavailableError("שירות ה-AI אינו מוגדר")
        item = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        if isinstance(item, Exception):
            raise item
        return item

    async def stream(
        self,
        *,
        system: str,
        messages: Sequence[ChatMessage],
        json_schema: JsonSchema | None = None,
        effort: Effort = "low",
        max_tokens: int = 4000,
    ) -> AsyncIterator[str | LLMResult]:
        self.calls.append({"system": system, "messages": list(messages), "schema": json_schema})
        text = self._next(system, messages)
        for i in range(0, len(text), 24):
            yield text[i : i + 24]
        yield LLMResult(
            text, self.model, sum(len(m["content"]) for m in messages) // 4, len(text) // 4
        )


def build_llm_client(settings: Settings) -> LLMClient:
    if settings.llm_provider == "anthropic":
        from app.services.ai.anthropic_client import AnthropicLLMClient

        return AnthropicLLMClient(
            settings.anthropic_api_key, settings.claude_model, settings.ai_timeout_seconds
        )
    return MockLLMClient()
