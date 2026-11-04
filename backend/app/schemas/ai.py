"""Request bodies and OpenAI structured-output (strict) schemas.

The `*Result` / `*Estimate` / `AdaptedRecipe` models are sent as `text_format` to
`client.responses.parse`, so they must not use defaults (strict mode requires every field).
"""

import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import Difficulty, Equipment, Kashrut, Lang
from app.schemas.recipe import Ingredient, RecipeContent, RecipeSummary


# ---- Structured outputs -------------------------------------------------------------------
class FridgeMatch(BaseModel):
    recipe_id: str
    match_score: int = Field(ge=0, le=100)
    missing_ingredients: list[str]


class FridgeSearchResult(BaseModel):
    matches: list[FridgeMatch]


class NutritionEstimate(BaseModel):
    """Per serving."""

    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    confidence: Literal["low", "medium", "high"]


class AdaptedRecipe(BaseModel):
    title: str
    description: str
    servings: int
    prep_minutes: int
    difficulty: Difficulty
    equipment: list[Equipment]
    kashrut: Kashrut
    ingredients: list[Ingredient]
    steps: list[str]
    changes_summary: list[str]
    feasible: bool
    reason: str | None

    def to_content(self) -> RecipeContent:
        return RecipeContent.model_validate(
            self.model_dump(exclude={"changes_summary", "feasible", "reason"})
        )


# ---- Request / response bodies ------------------------------------------------------------
class FridgeSearchRequest(BaseModel):
    ingredients: list[str] = Field(min_length=1, max_length=50)
    lang: Lang
    max_minutes: int | None = None
    difficulty: Difficulty | None = None
    equipment: list[Equipment] = []
    servings: int | None = None
    kashrut: Kashrut | None = None


class FridgeSearchItem(BaseModel):
    recipe: RecipeSummary
    match_score: int
    missing_ingredients: list[str]


class FridgeSearchResponse(BaseModel):
    results: list[FridgeSearchItem]


class AdaptRequest(BaseModel):
    recipe_id: uuid.UUID
    instruction: str = Field(min_length=1, max_length=500)


class ChatRequest(BaseModel):
    recipe_id: uuid.UUID
    message: str = Field(min_length=1, max_length=500)
    previous_response_id: str | None = None
