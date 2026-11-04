"""Catalog queries shared by the recipe list, smart search and the assistant."""

from dataclasses import dataclass, field, replace
from typing import Any

from sqlalchemy import Select, String, cast, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Difficulty,
    DishType,
    Ingredient,
    KosherType,
    Recipe,
    RecipeIngredient,
    RecipeStatus,
)


@dataclass(frozen=True)
class RecipeFilters:
    kosher_type: KosherType | None = None
    dish_type: DishType | None = None
    difficulty: Difficulty | None = None
    max_minutes: int | None = None
    text: str | None = None
    include_ingredients: tuple[str, ...] = field(default_factory=tuple)
    exclude_ingredients: tuple[str, ...] = field(default_factory=tuple)
    diet_tags: tuple[str, ...] = field(default_factory=tuple)


RecipeSelect = Select[Any]

# Field -> Hebrew phrase used in "N recipes found without <phrase>" suggestions.
RELAX_LABELS: dict[str, str] = {
    "max_minutes": "מגבלת הזמן",
    "difficulty": "רמת הקושי",
    "dish_type": "סוג המנה",
    "kosher_type": "הסוג (בשרי/חלבי/פרווה)",
    "include_ingredients": "הרכיבים הנדרשים",
    "exclude_ingredients": "הרכיבים המוחרגים",
    "diet_tags": "מגבלות התזונה",
    "text": "מילות החיפוש",
}


def _ingredient_match(name: str):  # type: ignore[no-untyped-def]
    pattern = f"%{name.strip()}%"
    return exists().where(
        RecipeIngredient.recipe_id == Recipe.id,
        RecipeIngredient.ingredient_id == Ingredient.id,
        or_(Ingredient.name.like(pattern), cast(Ingredient.aliases, String).like(pattern)),
    )


def apply_filters(stmt: RecipeSelect, f: RecipeFilters) -> RecipeSelect:
    if f.kosher_type:
        stmt = stmt.where(Recipe.kosher_type == f.kosher_type)
    if f.dish_type:
        stmt = stmt.where(Recipe.dish_type == f.dish_type)
    if f.difficulty:
        stmt = stmt.where(Recipe.difficulty == f.difficulty)
    if f.max_minutes:
        stmt = stmt.where(Recipe.prep_minutes + Recipe.cook_minutes <= f.max_minutes)
    if f.text:
        pattern = f"%{f.text.strip()}%"
        stmt = stmt.where(
            or_(
                Recipe.title.like(pattern),
                Recipe.description.like(pattern),
                _ingredient_match(f.text),
            )
        )
    for name in f.include_ingredients:
        stmt = stmt.where(_ingredient_match(name))
    for name in f.exclude_ingredients:
        stmt = stmt.where(~_ingredient_match(name))
    for tag in f.diet_tags:
        stmt = stmt.where(cast(Recipe.diet_tags, String).like(f'%"{tag}"%'))
    return stmt


def published() -> RecipeSelect:
    return select(Recipe).where(Recipe.status == RecipeStatus.PUBLISHED)


def with_card_options(stmt: RecipeSelect) -> RecipeSelect:
    return stmt.options(selectinload(Recipe.images))


def count(db: Session, f: RecipeFilters) -> int:
    stmt = apply_filters(published(), f)
    return db.scalar(select(func.count()).select_from(stmt.subquery())) or 0


def search(db: Session, f: RecipeFilters, limit: int = 24, offset: int = 0) -> list[Recipe]:
    stmt = with_card_options(apply_filters(published(), f))
    stmt = stmt.order_by(Recipe.view_count.desc(), Recipe.id).offset(offset).limit(limit)
    return list(db.scalars(stmt))


def active_fields(f: RecipeFilters) -> list[str]:
    return [name for name in RELAX_LABELS if getattr(f, name)]


@dataclass(frozen=True)
class Relaxation:
    remove: str
    count: int
    message: str


def relaxations(db: Session, f: RecipeFilters) -> list[Relaxation]:
    """For each active filter, how many recipes match without it (most results first)."""
    result: list[Relaxation] = []
    for name in active_fields(f):
        cleared: dict[str, Any] = {name: () if isinstance(getattr(f, name), tuple) else None}
        n = count(db, replace(f, **cleared))
        if n:
            result.append(Relaxation(name, n, f"נמצאו {n} מתכונים בלי {RELAX_LABELS[name]}"))
    return sorted(result, key=lambda r: -r.count)
