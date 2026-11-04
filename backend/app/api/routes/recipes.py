from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.deps import DbSession
from app.domain.servings import scale_quantity
from app.models import Difficulty, DishType, KosherType, Recipe, RecipeIngredient, RecipeStatus
from app.schemas.recipe import IngredientLine, Page, RecipeCard, RecipeDetail, StepOut

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("", response_model=Page[RecipeCard], summary="רשימת מתכונים עם מסננים ועימוד")
def list_recipes(
    db: DbSession,
    kosher_type: KosherType | None = None,
    dish_type: DishType | None = None,
    difficulty: Difficulty | None = None,
    max_minutes: Annotated[int | None, Query(ge=1)] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 24,
) -> Page[RecipeCard]:
    stmt = select(Recipe).where(Recipe.status == RecipeStatus.PUBLISHED)
    if kosher_type:
        stmt = stmt.where(Recipe.kosher_type == kosher_type)
    if dish_type:
        stmt = stmt.where(Recipe.dish_type == dish_type)
    if difficulty:
        stmt = stmt.where(Recipe.difficulty == difficulty)
    if max_minutes:
        stmt = stmt.where(Recipe.prep_minutes + Recipe.cook_minutes <= max_minutes)
    if q:
        stmt = stmt.where(Recipe.title.contains(q))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Recipe.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return Page(
        items=[RecipeCard.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{slug}", response_model=RecipeDetail, summary="מתכון מלא")
def get_recipe(
    slug: str, db: DbSession, servings: Annotated[int | None, Query(ge=1, le=100)] = None
) -> RecipeDetail:
    recipe = db.scalar(
        select(Recipe)
        .where(Recipe.slug == slug, Recipe.status == RecipeStatus.PUBLISHED)
        .options(
            selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient),
            selectinload(Recipe.steps),
        )
    )
    if recipe is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "המתכון לא נמצא")

    target = servings or recipe.servings
    card = RecipeCard.model_validate(recipe)
    return RecipeDetail(
        **card.model_dump(),
        prep_minutes=recipe.prep_minutes,
        cook_minutes=recipe.cook_minutes,
        servings=target,
        time_tags=recipe.time_tags,
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
