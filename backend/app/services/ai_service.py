"""The only module that talks to OpenAI (Responses API). Every call is logged to ai_usage_log."""

import json
import logging
from typing import Any, TypeVar

import openai
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import AiFeature, AiUsageLog, Recipe
from app.schemas.ai import AdaptedRecipe, FridgeMatch, FridgeSearchResult, NutritionEstimate
from app.services import prompts

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

MAX_FRIDGE_RESULTS = 10
MAX_TOOL_ROUNDS = 3  # per chat message

# Function tools for the chat (strict mode). The chat loop itself is not implemented yet.
CHAT_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "adapt_recipe",
        "description": "Adapt the open recipe according to a free-text instruction.",
        "parameters": {
            "type": "object",
            "properties": {"instruction": {"type": "string"}},
            "required": ["instruction"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "scale_servings",
        "description": "Scale the open recipe to a different number of servings.",
        "parameters": {
            "type": "object",
            "properties": {"servings": {"type": "integer"}},
            "required": ["servings"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


class AiUnavailableError(Exception):
    """The AI call failed or is not configured; callers return a friendly message."""


class AiRefusalError(AiUnavailableError):
    """The model declined to answer; the message carries the refusal text."""


def _refusal_text(response: Any) -> str | None:
    """Return the model's refusal text, if the response contains one."""
    for item in getattr(response, "output", None) or []:
        for part in getattr(item, "content", None) or []:
            if getattr(part, "type", None) == "refusal":
                return str(part.refusal)
    return None


def _is_retryable(exc: Exception) -> bool:
    return isinstance(exc, openai.RateLimitError) or (
        isinstance(exc, openai.APIStatusError) and exc.status_code >= 500
    )


class AiService:
    def __init__(self, client: openai.OpenAI | None, model: str) -> None:
        self._client = client
        self.model = model

    @classmethod
    def from_settings(cls, settings: Settings) -> "AiService":
        client = None
        if settings.openai_api_key:
            # Retries are handled here (exactly one), so the SDK's own are disabled.
            client = openai.OpenAI(
                api_key=settings.openai_api_key,
                timeout=settings.ai_timeout_seconds,
                max_retries=0,
            )
        return cls(client, settings.openai_model)

    def log_usage(
        self, db: Session, feature: AiFeature, response: Any
    ) -> None:  # response: openai Response
        usage = getattr(response, "usage", None)
        db.add(
            AiUsageLog(
                feature=feature,
                model=self.model,
                input_tokens=getattr(usage, "input_tokens", 0) or 0,
                output_tokens=getattr(usage, "output_tokens", 0) or 0,
                response_id=getattr(response, "id", None),
            )
        )
        db.commit()

    def parse(
        self, db: Session, feature: AiFeature, instructions: str, payload: str, schema: type[T]
    ) -> T:
        """Call the model with Structured Outputs; the schema comes from the Pydantic model."""
        if self._client is None:
            raise AiUnavailableError("OPENAI_API_KEY is not configured")
        last: Exception | None = None
        for _attempt in range(2):  # one retry on 429 / 5xx
            try:
                response = self._client.responses.parse(
                    model=self.model,
                    instructions=instructions,
                    input=payload,
                    text_format=schema,
                )
            except ValidationError as exc:  # the model returned JSON that does not fit the schema
                log.warning("openai invalid structured output (%s): %s", feature.value, exc)
                raise AiUnavailableError("invalid structured output") from exc
            except openai.OpenAIError as exc:
                last = exc
                if _is_retryable(exc):
                    continue
                break
            self.log_usage(db, feature, response)
            refusal = _refusal_text(response)
            if refusal is not None:
                raise AiRefusalError(f"model refused: {refusal}")
            if response.output_parsed is None:
                raise AiUnavailableError("empty structured output")
            return response.output_parsed
        log.warning("openai call failed (%s): %s", feature.value, last)
        raise AiUnavailableError(str(last)) from last

    # ---- Features ---------------------------------------------------------------------
    def fridge_search(
        self, db: Session, ingredients: list[str], candidates: list[Recipe]
    ) -> list[FridgeMatch]:
        compact = [
            {"id": str(r.id), "title": r.title, "ingredients": [i["name"] for i in r.ingredients]}
            for r in candidates
        ]
        payload = json.dumps({"have": ingredients, "recipes": compact}, ensure_ascii=False)
        result = self.parse(
            db, AiFeature.FRIDGE_SEARCH, prompts.FRIDGE_SEARCH, payload, FridgeSearchResult
        )
        known = {str(r.id) for r in candidates}
        matches = [m for m in result.matches if m.recipe_id in known]
        matches.sort(key=lambda m: m.match_score, reverse=True)
        return matches[:MAX_FRIDGE_RESULTS]

    def estimate_nutrition(self, db: Session, recipe: Recipe) -> NutritionEstimate:
        payload = json.dumps(
            {"servings": recipe.servings, "ingredients": recipe.ingredients}, ensure_ascii=False
        )
        return self.parse(db, AiFeature.NUTRITION, prompts.NUTRITION, payload, NutritionEstimate)

    def adapt_recipe(self, db: Session, recipe: Recipe, instruction: str) -> AdaptedRecipe:
        payload = json.dumps(
            {
                "recipe": {
                    "title": recipe.title,
                    "description": recipe.description,
                    "servings": recipe.servings,
                    "prep_minutes": recipe.prep_minutes,
                    "difficulty": recipe.difficulty.value,
                    "equipment": [e.value for e in recipe.equipment],
                    "kashrut": recipe.kashrut.value,
                    "ingredients": recipe.ingredients,
                    "steps": recipe.steps,
                },
                "instruction": instruction,
            },
            ensure_ascii=False,
        )
        return self.parse(db, AiFeature.ADAPT, prompts.ADAPT, payload, AdaptedRecipe)
