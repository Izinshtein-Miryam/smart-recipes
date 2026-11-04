"""Demo data loader. Extend seed_data.json towards the ~50 demo recipes in the spec."""

import json
from importlib import resources
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Ingredient, Recipe, RecipeStatus
from app.services.embeddings.provider import EmbeddingProvider, MockEmbeddingProvider
from app.services.recipe_writer import IngredientLineIn, StepIn, set_content


def load_seed_data() -> dict[str, Any]:
    text = resources.files("app.seed").joinpath("seed_data.json").read_text(encoding="utf-8")
    data: dict[str, Any] = json.loads(text)
    return data


def seed(db: Session, embedder: EmbeddingProvider | None = None) -> int:
    """Insert seed data idempotently. Returns the number of recipes created."""
    embedder = embedder or MockEmbeddingProvider()
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
        recipe = Recipe(**r, status=RecipeStatus.PUBLISHED)
        set_content(
            db,
            recipe,
            [IngredientLineIn(by_name[n].id, q, u) for n, q, u in lines],
            [StepIn(t, s) for t, s in steps],
            embedder,
        )
        db.add(recipe)
        created += 1
    db.commit()
    return created
