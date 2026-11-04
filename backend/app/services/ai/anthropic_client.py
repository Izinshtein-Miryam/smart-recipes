"""Claude API implementation of `LLMClient` (Anthropic Python SDK)."""

from collections.abc import AsyncIterator, Sequence
from typing import Any

import anthropic

from app.services.ai.client import (
    ChatMessage,
    Effort,
    JsonSchema,
    LLMRefusalError,
    LLMResult,
    LLMUnavailableError,
)


class AnthropicLLMClient:
    def __init__(self, api_key: str, model: str, timeout: float) -> None:
        self.model = model
        self._client = anthropic.AsyncAnthropic(api_key=api_key or None, timeout=timeout)

    async def stream(
        self,
        *,
        system: str,
        messages: Sequence[ChatMessage],
        json_schema: JsonSchema | None = None,
        effort: Effort = "low",
        max_tokens: int = 4000,
    ) -> AsyncIterator[str | LLMResult]:
        output_config: dict[str, Any] = {"effort": effort}
        if json_schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": json_schema}
        try:
            # Server-side fallback: if the model declines, the API retries on a fallback model.
            async with self._client.beta.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[dict(m) for m in messages],  # type: ignore[misc]
                output_config=output_config,  # type: ignore[arg-type]
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            ) as stream:
                async for text in stream.text_stream:
                    yield text
                final = await stream.get_final_message()
        except anthropic.APITimeoutError as e:
            raise LLMUnavailableError("שירות ה-AI לא הגיב בזמן") from e
        except anthropic.RateLimitError as e:
            raise LLMUnavailableError("שירות ה-AI עמוס כרגע, נסו שוב בעוד רגע") from e
        except anthropic.APIStatusError as e:
            raise LLMUnavailableError(f"שגיאה משירות ה-AI ({e.status_code})") from e
        except anthropic.APIConnectionError as e:
            raise LLMUnavailableError("אין חיבור לשירות ה-AI") from e

        if final.stop_reason == "refusal":
            raise LLMRefusalError("הבקשה לא אושרה על ידי שירות ה-AI")
        text = "".join(block.text for block in final.content if block.type == "text")
        yield LLMResult(text, final.model, final.usage.input_tokens, final.usage.output_tokens)
