"""Create/update recipes from validated input: ingredients, steps, kosher type and embedding."""

import secrets
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.kosher import MeatDairyMixError, derive_recipe_kosher_type
from app.models import Ingredient, KosherType, Recipe, RecipeIngredient, RecipeStep
from app.services.embeddings.provider import EmbeddingProvider, to_blob


class RecipeValidationError(ValueError):
    """Input is structurally valid but violates a business rule (message is user-facing)."""


@dataclass(frozen=True)
class IngredientLineIn:
    ingredient_id: int
    quantity: float | None
    unit: str | None
    note: str | None = None


@dataclass(frozen=True)
class StepIn:
    text: str
    timer_seconds: int | None = None
    ingredient_ids: tuple[int, ...] = ()


def new_slug(prefix: str = "recipe") -> str:
    return f"{prefix}-{secrets.token_hex(4)}"


def embedding_text(recipe: Recipe, ingredient_names: list[str]) -> str:
    return " | ".join([recipe.title, recipe.description, ", ".join(ingredient_names)])


def set_content(
    db: Session,
    recipe: Recipe,
    lines: list[IngredientLineIn],
    steps: list[StepIn],
    embedder: EmbeddingProvider,
) -> None:
    """Replace ingredients and steps, derive the kosher type and recompute the embedding."""
    ids = [line.ingredient_id for line in lines]
    found = {i.id: i for i in db.scalars(select(Ingredient).where(Ingredient.id.in_(ids)))}
    missing = sorted(set(ids) - set(found))
    if missing:
        raise RecipeValidationError(f"רכיבים לא קיימים: {missing}")
    for step in steps:
        unknown = set(step.ingredient_ids) - set(ids)
        if unknown:
            raise RecipeValidationError(f"שלב מפנה לרכיבים שאינם במתכון: {sorted(unknown)}")

    try:
        recipe.kosher_type = derive_recipe_kosher_type(
            KosherType(found[i].kosher_type) for i in ids
        )
    except MeatDairyMixError as e:
        raise RecipeValidationError(str(e)) from e
    recipe.ingredients = [
        RecipeIngredient(
            ingredient_id=line.ingredient_id,
            quantity=line.quantity,
            unit=line.unit,
            note=line.note,
            order=n,
        )
        for n, line in enumerate(lines)
    ]
    recipe.steps = [
        RecipeStep(
            order=n + 1,
            text=s.text,
            timer_seconds=s.timer_seconds,
            ingredient_ids=list(s.ingredient_ids),
        )
        for n, s in enumerate(steps)
    ]
    names = [found[i].name for i in ids]
    recipe.embedding = to_blob(embedder.embed(embedding_text(recipe, names)))


def find_ingredient(db: Session, name: str) -> Ingredient | None:
    """Match by exact name, then by alias (both trimmed, case-insensitive)."""
    key = name.strip().lower()
    for ing in db.scalars(select(Ingredient)):
        if ing.name.lower() == key or key in (a.lower() for a in ing.aliases):
            return ing
    return None
