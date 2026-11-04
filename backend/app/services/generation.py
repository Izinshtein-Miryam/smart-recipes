"""Smart generation: validate the model's recipe and keep unsaved results in memory."""

import json
import secrets
import time
from dataclasses import dataclass, field

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.domain.kosher import MeatDairyMixError, derive_recipe_kosher_type
from app.models import Difficulty, DishType, Ingredient, KosherType, TimeTag
from app.services.recipe_writer import find_ingredient


class GeneratedIngredient(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    quantity: float = Field(gt=0)
    unit: str = Field(min_length=1, max_length=30)
    kosher_type: KosherType
    note: str | None = None
    # Filled in by validation, not by the model:
    ingredient_id: int | None = None
    not_provided: bool = False


class GeneratedStep(BaseModel):
    text: str = Field(min_length=1)
    timer_seconds: int | None = Field(default=None, ge=1)


class GeneratedRecipe(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str
    servings: int = Field(ge=1, le=100)
    prep_minutes: int = Field(ge=0)
    cook_minutes: int = Field(ge=0)
    difficulty: Difficulty
    dish_type: DishType
    kosher_type: KosherType
    diet_tags: list[str]
    time_tags: list[TimeTag]
    ingredients: list[GeneratedIngredient] = Field(min_length=1)
    steps: list[GeneratedStep] = Field(min_length=1)
    changes: list[str] = Field(default_factory=list)


class GenerationRejectedError(ValueError):
    """The output parsed but broke a rule; the message is fed back into the retry."""


_COMPATIBLE: dict[KosherType, set[KosherType]] = {
    KosherType.MEAT: {KosherType.MEAT, KosherType.PARVE},
    KosherType.DAIRY: {KosherType.DAIRY, KosherType.PARVE},
    KosherType.PARVE: {KosherType.PARVE},
}


def validate_generated(
    db: Session,
    raw: str,
    *,
    requested_kosher: KosherType | None = None,
    provided: list[str] | None = None,
    basic_names: list[str] | None = None,
) -> GeneratedRecipe:
    """Parse, map ingredients to the ingredients table and enforce the generation rules.

    Raises `GenerationRejectedError` with a reason suitable for a retry prompt.
    """
    try:
        recipe = GeneratedRecipe.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError) as e:
        raise GenerationRejectedError(f"הפלט אינו תואם לסכמה: {e}") from e

    provided_keys = {p.strip().lower() for p in provided or []}
    provided_ids: set[int] = set()
    for name in provided or []:
        ing = find_ingredient(db, name)
        if ing:
            provided_ids.add(ing.id)
    basic = {b.strip().lower() for b in basic_names or []}

    types: list[KosherType] = []
    for item in recipe.ingredients:
        known: Ingredient | None = find_ingredient(db, item.name)
        if known:
            item.ingredient_id = known.id
            item.kosher_type = KosherType(known.kosher_type)  # the table is authoritative
        types.append(item.kosher_type)

        if provided is not None:
            is_provided = item.name.strip().lower() in provided_keys or (
                known is not None and known.id in provided_ids
            )
            if not is_provided:
                is_basic = item.name.strip().lower() in basic or bool(known and known.is_basic)
                if not is_basic:
                    raise GenerationRejectedError(
                        f'הרכיב "{item.name}" לא הוזן ואינו רכיב בסיס מותר'
                    )
                item.not_provided = True

    try:
        derived = derive_recipe_kosher_type(types)
    except MeatDairyMixError as e:
        raise GenerationRejectedError("המתכון מערבב רכיבים בשריים וחלביים") from e
    if requested_kosher and derived not in _COMPATIBLE[requested_kosher]:
        raise GenerationRejectedError(
            f"התבקש מתכון מסוג {requested_kosher.value} אך התקבל {derived.value}"
        )
    recipe.kosher_type = derived
    return recipe


@dataclass
class GeneratedEntry:
    recipe: GeneratedRecipe
    created_at: float = field(default_factory=time.monotonic)
    saved_slug: str | None = None


class GeneratedStore:
    """Unsaved generated recipes, kept in memory for a limited time."""

    def __init__(self, ttl_seconds: float = 6 * 3600, max_items: int = 500) -> None:
        self.ttl = ttl_seconds
        self.max_items = max_items
        self._items: dict[str, GeneratedEntry] = {}

    def add(self, recipe: GeneratedRecipe) -> str:
        self._evict()
        key = secrets.token_urlsafe(12)
        self._items[key] = GeneratedEntry(recipe)
        return key

    def get(self, key: str) -> GeneratedEntry | None:
        self._evict()
        return self._items.get(key)

    def _evict(self) -> None:
        now = time.monotonic()
        for key in [k for k, v in self._items.items() if now - v.created_at > self.ttl]:
            del self._items[key]
        while len(self._items) >= self.max_items:
            del self._items[next(iter(self._items))]


generated_store = GeneratedStore()
