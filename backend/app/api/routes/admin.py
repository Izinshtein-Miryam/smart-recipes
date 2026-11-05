"""Admin endpoints: login and the approval queue (Bearer JWT)."""

import contextlib
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.config import get_settings
from app.core.deps import AdminOnly, AiDep, DbSession
from app.core.security import create_admin_token, verify_password
from app.models import Recipe, RecipeStatus
from app.schemas.admin import LoginRequest, TokenResponse
from app.schemas.recipe import RecipeOut, RecipeUpdate
from app.services import storage
from app.services.ai_service import AiUnavailableError

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest) -> TokenResponse:
    if not verify_password(body.password, get_settings().admin_password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid password")
    return TokenResponse(access_token=create_admin_token())


def _get(db: DbSession, recipe_id: uuid.UUID) -> Recipe:
    recipe = db.get(Recipe, recipe_id)
    if recipe is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "recipe not found")
    return recipe


@router.get("/recipes", response_model=list[RecipeOut], dependencies=[AdminOnly])
def queue(
    db: DbSession, status_: Annotated[RecipeStatus, Query(alias="status")] = RecipeStatus.PENDING
) -> list[Recipe]:
    stmt = select(Recipe).where(Recipe.status == status_).order_by(Recipe.created_at)
    return list(db.scalars(stmt))


@router.put("/recipes/{recipe_id}", response_model=RecipeOut, dependencies=[AdminOnly])
def update(recipe_id: uuid.UUID, body: RecipeUpdate, db: DbSession) -> Recipe:
    recipe = _get(db, recipe_id)
    for field, value in body.model_dump(exclude={"ingredients", "steps"}).items():
        setattr(recipe, field, value)
    recipe.ingredients = [i.model_dump() for i in body.ingredients]
    recipe.steps = body.steps
    db.commit()
    return recipe


@router.post("/recipes/{recipe_id}/approve", response_model=RecipeOut, dependencies=[AdminOnly])
def approve(recipe_id: uuid.UUID, db: DbSession, ai: AiDep) -> Recipe:
    """Publishes the recipe. Safe to call again on an approved recipe to retry nutrition."""
    recipe = _get(db, recipe_id)
    if recipe.status == RecipeStatus.REJECTED:
        raise HTTPException(status.HTTP_409_CONFLICT, "recipe was rejected")
    # On AI failure approve anyway: nutrition stays null and the admin can call approve again.
    with contextlib.suppress(AiUnavailableError):
        recipe.nutrition = ai.estimate_nutrition(db, recipe).model_dump()
    if recipe.image_path:
        recipe.image_path = storage.promote(recipe.image_path)
    recipe.status = RecipeStatus.APPROVED
    recipe.approved_at = recipe.approved_at or datetime.now(UTC)
    db.commit()
    return recipe


@router.post("/recipes/{recipe_id}/reject", response_model=RecipeOut, dependencies=[AdminOnly])
def reject(recipe_id: uuid.UUID, db: DbSession) -> Recipe:
    recipe = _get(db, recipe_id)
    recipe.status = RecipeStatus.REJECTED
    db.commit()  # the image is deleted by `python -m app.cli purge-rejected` after 7 days
    return recipe
