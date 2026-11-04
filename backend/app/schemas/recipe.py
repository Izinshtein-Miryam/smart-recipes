from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import Difficulty, DishType, KosherType, RecipeSource


class RecipeCard(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    title: str
    description: str
    kosher_type: KosherType
    dish_type: DishType
    difficulty: Difficulty
    total_minutes: int
    diet_tags: list[str]
    source: RecipeSource


class IngredientLine(BaseModel):
    ingredient_id: int
    name: str
    quantity: float | None
    unit: str | None
    note: str | None


class StepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order: int
    text: str
    timer_seconds: int | None
    ingredient_ids: list[int]


class RecipeDetail(RecipeCard):
    prep_minutes: int
    cook_minutes: int
    servings: int
    time_tags: list[str]
    ingredients: list[IngredientLine]
    steps: list[StepOut]
    created_at: datetime


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int
