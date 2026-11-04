"""Recipe schemas. `RecipeContent` is shared with the AI structured-output schemas."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Difficulty, Equipment, Kashrut, Lang, RecipeStatus


class Ingredient(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    quantity: float | None
    unit: str | None
    note: str | None


class Nutrition(BaseModel):
    """Per serving."""

    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    confidence: Literal["low", "medium", "high"] | None = None


class RecipeContent(BaseModel):
    """The fields a visitor submits and the AI may adapt."""

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(max_length=1000)
    servings: int = Field(ge=1, le=100)
    prep_minutes: int = Field(ge=1, le=24 * 60)
    difficulty: Difficulty
    equipment: list[Equipment]
    kashrut: Kashrut
    ingredients: list[Ingredient] = Field(min_length=1, max_length=100)
    steps: list[str] = Field(min_length=1, max_length=100)


class RecipeCreate(RecipeContent):
    lang: Lang
    source_recipe_id: uuid.UUID | None = None


class RecipeUpdate(RecipeContent):
    lang: Lang


class RecipeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lang: Lang
    title: str
    description: str
    servings: int
    prep_minutes: int
    difficulty: Difficulty
    equipment: list[Equipment]
    kashrut: Kashrut
    image_url: str | None


class RecipeOut(RecipeSummary):
    ingredients: list[Ingredient]
    steps: list[str]
    nutrition: Nutrition | None
    status: RecipeStatus
    source_recipe_id: uuid.UUID | None
    created_at: datetime
    approved_at: datetime | None
