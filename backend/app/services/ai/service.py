"""Single entry point for text-AI calls. Records every call in the `ai_calls` table."""

import time

from sqlalchemy.orm import Session

from app.models import AICall, AIFeature
from app.services.ai.client import LLMClient, LLMResult


class AIService:
    def __init__(self, client: LLMClient, db: Session) -> None:
        self.client = client
        self.db = db

    async def complete(
        self, feature: AIFeature, system: str, user: str, user_id: int | None = None
    ) -> LLMResult:
        start = time.perf_counter()
        try:
            result = await self.client.complete(system, user)
        except Exception:
            self._log(feature, user_id, None, start, "error")
            raise
        self._log(feature, user_id, result, start, "ok")
        return result

    def _log(
        self,
        feature: AIFeature,
        user_id: int | None,
        result: LLMResult | None,
        start: float,
        status: str,
    ) -> None:
        self.db.add(
            AICall(
                user_id=user_id,
                feature=feature,
                model=result.model if result else self.client.model,
                input_tokens=result.input_tokens if result else 0,
                output_tokens=result.output_tokens if result else 0,
                cost_usd=0.0,  # TODO: compute from a per-model price table
                latency_ms=int((time.perf_counter() - start) * 1000),
                status=status,
            )
        )
        self.db.commit()
