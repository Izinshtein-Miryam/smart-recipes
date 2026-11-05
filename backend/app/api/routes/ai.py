"""AI endpoints (public). Failures surface as 503 `ai_unavailable`, see main.py."""

import json
import uuid
from collections.abc import Iterator

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse

from app.core.deps import AiDep, DbSession
from app.db import SessionLocal
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
def chat(body: ChatRequest, db: DbSession, ai: AiDep) -> EventSourceResponse:
    recipe = _approved_recipe(db, body.recipe_id)
    db.expunge(recipe)  # the stream outlives the request-scoped session

    def events() -> Iterator[dict[str, str]]:
        # The request-scoped session is closed before streaming starts, so open our own.
        with SessionLocal() as stream_db:
            for ev in ai.chat_stream(stream_db, recipe, body.message, body.previous_response_id):
                yield {"event": ev["event"], "data": json.dumps(ev["data"], ensure_ascii=False)}

    return EventSourceResponse(events())
