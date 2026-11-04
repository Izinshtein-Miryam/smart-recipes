"""ORM -> response schema conversion shared by several routers."""

import json
from typing import Any

from app.domain.servings import scale_quantity
from app.models import Recipe
from app.schemas.recipe import IngredientLine, RecipeCard, RecipeDetail, StepOut


def to_card(recipe: Recipe) -> RecipeCard:
    return RecipeCard.model_validate(recipe)


def to_cards(recipes: list[Recipe]) -> list[RecipeCard]:
    return [to_card(r) for r in recipes]


def to_detail(recipe: Recipe, servings: int | None = None) -> RecipeDetail:
    target = servings or recipe.servings
    return RecipeDetail(
        **to_card(recipe).model_dump(),
        prep_minutes=recipe.prep_minutes,
        cook_minutes=recipe.cook_minutes,
        servings=target,
        base_servings=recipe.servings,
        time_tags=recipe.time_tags,
        status=recipe.status,
        ingredients=[
            IngredientLine(
                ingredient_id=ri.ingredient_id,
                name=ri.ingredient.name,
                quantity=scale_quantity(ri.quantity, recipe.servings, target),
                unit=ri.unit,
                note=ri.note,
            )
            for ri in recipe.ingredients
        ],
        steps=[StepOut.model_validate(s) for s in recipe.steps],
        created_at=recipe.created_at,
    )


def sse(event: str, data: Any) -> str:
    """Format one Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
