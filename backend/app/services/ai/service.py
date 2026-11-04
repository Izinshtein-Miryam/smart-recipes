"""Single entry point for text-AI calls. Every call is recorded in the `ai_calls` table."""

import time
from collections.abc import AsyncIterator, Sequence

from sqlalchemy.orm import Session

from app.models import AICall, AIFeature
from app.services.ai.client import ChatMessage, Effort, JsonSchema, LLMClient, LLMResult
from app.services.ai.pricing import cost_usd


class AIService:
    def __init__(self, client: LLMClient, db: Session, user_id: int | None = None) -> None:
        self.client = client
        self.db = db
        self.user_id = user_id

    async def stream(
        self,
        feature: AIFeature,
        *,
        system: str,
        messages: Sequence[ChatMessage],
        json_schema: JsonSchema | None = None,
        effort: Effort = "low",
        max_tokens: int = 4000,
    ) -> AsyncIterator[str | LLMResult]:
        """Proxy `LLMClient.stream`, logging the call when it ends (successfully or not)."""
        start = time.perf_counter()
        result: LLMResult | None = None
        try:
            async for chunk in self.client.stream(
                system=system,
                messages=messages,
                json_schema=json_schema,
                effort=effort,
                max_tokens=max_tokens,
            ):
                if isinstance(chunk, LLMResult):
                    result = chunk
                yield chunk
        finally:
            self._log(feature, result, start)

    async def complete(
        self,
        feature: AIFeature,
        *,
        system: str,
        messages: Sequence[ChatMessage],
        json_schema: JsonSchema | None = None,
        effort: Effort = "low",
        max_tokens: int = 4000,
    ) -> LLMResult:
        result: LLMResult | None = None
        async for chunk in self.stream(
            feature,
            system=system,
            messages=messages,
            json_schema=json_schema,
            effort=effort,
            max_tokens=max_tokens,
        ):
            if isinstance(chunk, LLMResult):
                result = chunk
        assert result is not None  # noqa: S101 - LLMClient contract
        return result

    def _log(self, feature: AIFeature, result: LLMResult | None, start: float) -> None:
        self.db.add(
            AICall(
                user_id=self.user_id,
                feature=feature,
                model=result.model if result else self.client.model,
                input_tokens=result.input_tokens if result else 0,
                output_tokens=result.output_tokens if result else 0,
                cost_usd=cost_usd(result.model, result.input_tokens, result.output_tokens)
                if result
                else 0.0,
                latency_ms=int((time.perf_counter() - start) * 1000),
                status="ok" if result else "error",
            )
        )
        self.db.commit()
