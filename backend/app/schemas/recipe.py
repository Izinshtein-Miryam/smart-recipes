from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import Difficulty, DishType, KosherType, RecipeSource, RecipeStatus, TimeTag


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
    image_url: str | None


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
    base_servings: int
    time_tags: list[str]
    status: RecipeStatus
    ingredients: list[IngredientLine]
    steps: list[StepOut]
    created_at: datetime


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int


# ---- Admin -----------------------------------------------------------------


class IngredientLineIn(BaseModel):
    ingredient_id: int
    quantity: float | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, max_length=30)
    note: str | None = Field(default=None, max_length=200)


class StepIn(BaseModel):
    text: str = Field(min_length=1)
    timer_seconds: int | None = Field(default=None, ge=1)
    ingredient_ids: list[int] = Field(default_factory=list)


class RecipeIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    slug: str | None = Field(default=None, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=200)
    description: str = ""
    dish_type: DishType
    difficulty: Difficulty
    prep_minutes: int = Field(ge=0)
    cook_minutes: int = Field(ge=0)
    servings: int = Field(ge=1, le=100)
    time_tags: list[TimeTag] = Field(default_factory=list)
    diet_tags: list[str] = Field(default_factory=list)
    status: RecipeStatus = RecipeStatus.DRAFT
    ingredients: list[IngredientLineIn] = Field(min_length=1)
    steps: list[StepIn] = Field(min_length=1)


class StatusIn(BaseModel):
    status: RecipeStatus


class AdminRecipeRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    title: str
    status: RecipeStatus
    source: RecipeSource
    kosher_type: KosherType
    dish_type: DishType
    owner_id: int | None
    view_count: int
    updated_at: datetime
