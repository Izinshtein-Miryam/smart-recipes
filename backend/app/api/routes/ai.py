"""AI endpoints (public). Failures surface as 503 `ai_unavailable`, see main.py."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import AiDep, DbSession
from app.models import Recipe, RecipeStatus
from app.schemas.ai import (
    AdaptedRecipe,
    AdaptRequest,
    ChatRequest,
    FridgeSearchItem,
    FridgeSearchRequest,
    FridgeSearchResponse,
)
from app.schemas.recipe import RecipeSummary

router = APIRouter(prefix="/ai", tags=["ai"])


def _approved_recipe(db: DbSession, recipe_id: uuid.UUID) -> Recipe:
    recipe = db.get(Recipe, recipe_id)
    if recipe is None or recipe.status != RecipeStatus.APPROVED:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "recipe not found")
    return recipe


@router.post("/fridge-search", response_model=FridgeSearchResponse)
def fridge_search(body: FridgeSearchRequest, db: DbSession, ai: AiDep) -> FridgeSearchResponse:
    stmt = select(Recipe).where(Recipe.status == RecipeStatus.APPROVED, Recipe.lang == body.lang)
    if body.max_minutes:
        stmt = stmt.where(Recipe.prep_minutes <= body.max_minutes)
    if body.difficulty:
        stmt = stmt.where(Recipe.difficulty == body.difficulty)
    if body.equipment:
        stmt = stmt.where(Recipe.equipment.contains(body.equipment))
    if body.servings:
        stmt = stmt.where(Recipe.servings == body.servings)
    if body.kashrut:
        stmt = stmt.where(Recipe.kashrut == body.kashrut)
    candidates = list(db.scalars(stmt))
    if not candidates:
        return FridgeSearchResponse(results=[])

    by_id = {str(r.id): r for r in candidates}
    matches = ai.fridge_search(db, body.ingredients, candidates)
    return FridgeSearchResponse(
        results=[
            FridgeSearchItem(
                recipe=RecipeSummary.model_validate(by_id[m.recipe_id]),
                match_score=m.match_score,
                missing_ingredients=m.missing_ingredients,
            )
            for m in matches
        ]
    )


@router.post("/adapt", response_model=AdaptedRecipe)
def adapt(body: AdaptRequest, db: DbSession, ai: AiDep) -> AdaptedRecipe:
    return ai.adapt_recipe(db, _approved_recipe(db, body.recipe_id), body.instruction)


@router.post("/chat")
def chat(_body: ChatRequest) -> None:
    # TODO: SSE stream (text_delta, tool_started, recipe_adapted, recipe_scaled, done, error)
    # with the tool loop limited to MAX_TOOL_ROUNDS. See docs/SPEC.md.
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "chat is not implemented yet")
