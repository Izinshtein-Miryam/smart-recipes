from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.core.deps import ContentManager, DbSession, Embeddings
from app.models import KosherType, Recipe, RecipeSource, RecipeStatus
from app.schemas.recipe import (
    AdminRecipeRow,
    IngredientLineIn,
    RecipeIn,
    StatusIn,
    StepIn,
)
from app.services import recipe_writer
from app.services.audit import log_action

router = APIRouter(prefix="/admin/recipes", tags=["admin"])


class AdminRecipeDetail(RecipeIn):
    id: int
    slug: str
    kosher_type: KosherType
    source: RecipeSource
    owner_id: int | None


def _detail(recipe: Recipe) -> AdminRecipeDetail:
    return AdminRecipeDetail(
        id=recipe.id,
        slug=recipe.slug,
        title=recipe.title,
        description=recipe.description,
        dish_type=recipe.dish_type,
        difficulty=recipe.difficulty,
        prep_minutes=recipe.prep_minutes,
        cook_minutes=recipe.cook_minutes,
        servings=recipe.servings,
        time_tags=recipe.time_tags,
        diet_tags=recipe.diet_tags,
        status=recipe.status,
        kosher_type=recipe.kosher_type,
        source=recipe.source,
        owner_id=recipe.owner_id,
        ingredients=[
            IngredientLineIn(
                ingredient_id=i.ingredient_id, quantity=i.quantity, unit=i.unit, note=i.note
            )
            for i in recipe.ingredients
        ],
        steps=[
            StepIn(text=s.text, timer_seconds=s.timer_seconds, ingredient_ids=s.ingredient_ids)
            for s in recipe.steps
        ],
    )


def _get(db: DbSession, recipe_id: int) -> Recipe:
    recipe = db.scalar(
        select(Recipe)
        .where(Recipe.id == recipe_id)
        .options(selectinload(Recipe.ingredients), selectinload(Recipe.steps))
    )
    if recipe is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "המתכון לא נמצא")
    return recipe


def _apply(db: DbSession, recipe: Recipe, body: RecipeIn, embedder: Embeddings) -> None:
    slug = body.slug or recipe.slug or recipe_writer.new_slug()
    clash = db.scalar(select(Recipe.id).where(Recipe.slug == slug, Recipe.id != recipe.id))
    if clash:
        raise HTTPException(status.HTTP_409_CONFLICT, "כתובת (slug) זו כבר בשימוש")
    recipe.slug = slug
    for field in (
        "title",
        "description",
        "dish_type",
        "difficulty",
        "prep_minutes",
        "cook_minutes",
        "servings",
        "diet_tags",
        "status",
    ):
        setattr(recipe, field, getattr(body, field))
    recipe.time_tags = [t.value for t in body.time_tags]
    try:
        recipe_writer.set_content(
            db,
            recipe,
            [
                recipe_writer.IngredientLineIn(i.ingredient_id, i.quantity, i.unit, i.note)
                for i in body.ingredients
            ],
            [
                recipe_writer.StepIn(s.text, s.timer_seconds, tuple(s.ingredient_ids))
                for s in body.steps
            ],
            embedder,
        )
    except recipe_writer.RecipeValidationError as e:
        db.rollback()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from e


@router.get("", response_model=list[AdminRecipeRow], summary="טבלת מתכונים לניהול")
def list_admin(
    db: DbSession,
    user: ContentManager,
    q: Annotated[str | None, Query(max_length=100)] = None,
    status_: Annotated[RecipeStatus | None, Query(alias="status")] = None,
    source: RecipeSource | None = None,
) -> list[Recipe]:
    stmt = select(Recipe).order_by(Recipe.updated_at.desc())
    if q:
        stmt = stmt.where(or_(Recipe.title.like(f"%{q}%"), Recipe.slug.like(f"%{q}%")))
    if status_:
        stmt = stmt.where(Recipe.status == status_)
    if source:
        stmt = stmt.where(Recipe.source == source)
    return list(db.scalars(stmt))


@router.get("/{recipe_id}", response_model=AdminRecipeDetail, summary="מתכון לעריכה")
def get_admin(recipe_id: int, db: DbSession, user: ContentManager) -> AdminRecipeDetail:
    return _detail(_get(db, recipe_id))


@router.post(
    "", response_model=AdminRecipeDetail, status_code=status.HTTP_201_CREATED, summary="יצירת מתכון"
)
def create(
    body: RecipeIn, db: DbSession, user: ContentManager, embedder: Embeddings
) -> AdminRecipeDetail:
    recipe = Recipe(source=RecipeSource.ADMIN, owner_id=user.id, slug="")
    _apply(db, recipe, body, embedder)
    db.add(recipe)
    db.flush()
    log_action(db, user, "recipe.create", "recipe", recipe.id, {"title": recipe.title})
    db.commit()
    return _detail(recipe)


@router.put("/{recipe_id}", response_model=AdminRecipeDetail, summary="עדכון מתכון")
def update(
    recipe_id: int, body: RecipeIn, db: DbSession, user: ContentManager, embedder: Embeddings
) -> AdminRecipeDetail:
    recipe = _get(db, recipe_id)
    _apply(db, recipe, body, embedder)
    log_action(db, user, "recipe.update", "recipe", recipe.id, {"status": recipe.status})
    db.commit()
    return _detail(recipe)


class StatusOut(BaseModel):
    id: int
    status: RecipeStatus


@router.patch("/{recipe_id}/status", response_model=StatusOut, summary="פרסום, הסתרה או טיוטה")
def set_status(recipe_id: int, body: StatusIn, db: DbSession, user: ContentManager) -> StatusOut:
    recipe = _get(db, recipe_id)
    old = recipe.status
    recipe.status = body.status
    log_action(db, user, "recipe.status", "recipe", recipe.id, {"from": old, "to": body.status})
    db.commit()
    return StatusOut(id=recipe.id, status=recipe.status)


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT, summary="מחיקת מתכון")
def delete(recipe_id: int, db: DbSession, user: ContentManager) -> Response:
    recipe = _get(db, recipe_id)
    log_action(db, user, "recipe.delete", "recipe", recipe.id, {"title": recipe.title})
    db.delete(recipe)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
