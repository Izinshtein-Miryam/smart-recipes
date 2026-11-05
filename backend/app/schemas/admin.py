from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.models import (
    Difficulty,
    DishType,
    ImageOrigin,
    KosherType,
    RecipeSource,
    RecipeStatus,
)


class IngredientLineIn(BaseModel):
    ingredient_id: int
    quantity: Annotated[float, Field(gt=0)] | None = None
    unit: Annotated[str, Field(max_length=30)] | None = None
    note: Annotated[str, Field(max_length=200)] | None = None


class StepIn(BaseModel):
    text: Annotated[str, Field(min_length=1)]
    timer_seconds: Annotated[int, Field(gt=0)] | None = None
    ingredient_ids: list[int] = []


class RecipeIn(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=200)]
    description: str = ""
    dish_type: DishType
    difficulty: Difficulty
    prep_minutes: Annotated[int, Field(ge=0)] = 0
    cook_minutes: Annotated[int, Field(ge=0)] = 0
    servings: Annotated[int, Field(ge=1, le=100)] = 4
    time_tags: list[str] = []
    diet_tags: list[str] = []
    status: RecipeStatus = RecipeStatus.DRAFT
    ingredients: list[IngredientLineIn] = []
    steps: list[StepIn] = []


class StatusIn(BaseModel):
    status: RecipeStatus


class AdminIngredientLine(IngredientLineIn):
    name: str


class AdminStep(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order: int
    text: str
    timer_seconds: int | None
    ingredient_ids: list[int]


class RecipeImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_path: str | None
    processed_path: str | None
    origin: ImageOrigin
    prompt: str | None
    is_primary: bool
    approved: bool


class ImageUpdate(BaseModel):
    approved: bool | None = None
    is_primary: bool | None = None


class AdminRecipeRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    title: str
    kosher_type: KosherType
    dish_type: DishType
    difficulty: Difficulty
    status: RecipeStatus
    source: RecipeSource
    view_count: int
    updated_at: datetime


class AdminRecipeDetail(AdminRecipeRow):
    description: str
    prep_minutes: int
    cook_minutes: int
    servings: int
    time_tags: list[str]
    diet_tags: list[str]
    ingredients: list[AdminIngredientLine]
    steps: list[AdminStep]
    images: list[RecipeImageOut]
