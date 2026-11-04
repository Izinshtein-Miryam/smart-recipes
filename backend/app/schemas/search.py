from typing import Literal

from pydantic import BaseModel, Field

from app.models import Difficulty, DishType, KosherType
from app.schemas.recipe import RecipeCard
from app.services.catalog import RecipeFilters


class Suggestion(BaseModel):
    type: Literal["recipe", "ingredient", "category"]
    label: str
    value: str


class FiltersModel(BaseModel):
    """Structured filters, as returned by the model and shown to the user as chips."""

    kosher_type: KosherType | None = None
    dish_type: DishType | None = None
    difficulty: Difficulty | None = None
    max_minutes: int | None = Field(default=None, ge=1)
    include_ingredients: list[str] = Field(default_factory=list)
    exclude_ingredients: list[str] = Field(default_factory=list)
    diet_tags: list[str] = Field(default_factory=list)
    text: str | None = None

    def to_filters(self) -> RecipeFilters:
        return RecipeFilters(
            kosher_type=self.kosher_type,
            dish_type=self.dish_type,
            difficulty=self.difficulty,
            max_minutes=self.max_minutes,
            text=self.text or None,
            include_ingredients=tuple(self.include_ingredients),
            exclude_ingredients=tuple(self.exclude_ingredients),
            diet_tags=tuple(self.diet_tags),
        )


class SmartSearchIn(BaseModel):
    query: str = Field(min_length=1, max_length=300)


class RelaxationOut(BaseModel):
    remove: str
    count: int
    message: str


class SmartSearchOut(BaseModel):
    query: str
    filters: FiltersModel
    results: list[RecipeCard]
    total: int
    relaxations: list[RelaxationOut]
    fallback: bool = Field(description="True when AI was unavailable and plain text search ran")
