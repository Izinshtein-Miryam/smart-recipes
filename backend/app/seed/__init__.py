"""Demo data loader. Extend seed_data.json towards the ~50 demo recipes in the spec."""

import json
from importlib import resources
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.kosher import derive_recipe_kosher_type
from app.models import (
    Ingredient,
    KosherType,
    Recipe,
    RecipeIngredient,
    RecipeStatus,
    RecipeStep,
)


def load_seed_data() -> dict[str, Any]:
    text = resources.files("app.seed").joinpath("seed_data.json").read_text(encoding="utf-8")
    data: dict[str, Any] = json.loads(text)
    return data


def seed(db: Session) -> int:
    """Insert seed data idempotently. Returns the number of recipes created."""
    data = load_seed_data()
    by_name: dict[str, Ingredient] = {i.name: i for i in db.scalars(select(Ingredient))}
    for item in data["ingredients"]:
        if item["name"] not in by_name:
            ing = Ingredient(**{"aliases": [], "is_basic": False, **item})
            db.add(ing)
            by_name[ing.name] = ing
    db.flush()

    created = 0
    for r in data["recipes"]:
        if db.scalar(select(Recipe).where(Recipe.slug == r["slug"])):
            continue
        lines = r.pop("ingredients")
        steps = r.pop("steps")
        kosher = derive_recipe_kosher_type(KosherType(by_name[n].kosher_type) for n, _, _ in lines)
        recipe = Recipe(**r, kosher_type=kosher, status=RecipeStatus.PUBLISHED)
        recipe.ingredients = [
            RecipeIngredient(ingredient_id=by_name[n].id, quantity=q, unit=u, order=i)
            for i, (n, q, u) in enumerate(lines)
        ]
        recipe.steps = [
            RecipeStep(order=i + 1, text=t, timer_seconds=s, ingredient_ids=[])
            for i, (t, s) in enumerate(steps)
        ]
        db.add(recipe)
        created += 1
    db.commit()
    return created
