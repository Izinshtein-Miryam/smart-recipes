from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.serializers import to_cards, to_detail
from app.core.deps import DbSession, OptionalUser
from app.models import (
    Difficulty,
    DishType,
    KosherType,
    Recipe,
    RecipeIngredient,
    RecipeStatus,
    Role,
)
from app.schemas.recipe import Page, RecipeCard, RecipeDetail
from app.services import catalog
from app.services.catalog import RecipeFilters

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("", response_model=Page[RecipeCard], summary="רשימת מתכונים עם מסננים ועימוד")
def list_recipes(
    db: DbSession,
    kosher_type: KosherType | None = None,
    dish_type: DishType | None = None,
    difficulty: Difficulty | None = None,
    max_minutes: Annotated[int | None, Query(ge=1)] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    include: Annotated[list[str] | None, Query(description="רכיבים שחייבים להופיע")] = None,
    exclude: Annotated[list[str] | None, Query(description="רכיבים להוצאה")] = None,
    diet: Annotated[list[str] | None, Query(description="מגבלות תזונה")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 24,
) -> Page[RecipeCard]:
    filters = RecipeFilters(
        kosher_type=kosher_type,
        dish_type=dish_type,
        difficulty=difficulty,
        max_minutes=max_minutes,
        text=q or None,
        include_ingredients=tuple(include or ()),
        exclude_ingredients=tuple(exclude or ()),
        diet_tags=tuple(diet or ()),
    )
    rows = catalog.search(db, filters, limit=page_size, offset=(page - 1) * page_size)
    return Page(
        items=to_cards(rows), total=catalog.count(db, filters), page=page, page_size=page_size
    )


@router.get("/{slug}", response_model=RecipeDetail, summary="מתכון מלא")
def get_recipe(
    slug: str,
    db: DbSession,
    user: OptionalUser,
    servings: Annotated[int | None, Query(ge=1, le=100)] = None,
) -> RecipeDetail:
    recipe = db.scalar(
        select(Recipe)
        .where(Recipe.slug == slug)
        .options(
            selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient),
            selectinload(Recipe.steps),
            selectinload(Recipe.images),
        )
    )
    # Drafts are visible only to their owner and to content managers.
    if recipe is None or (
        recipe.status != RecipeStatus.PUBLISHED
        and not (user and (user.id == recipe.owner_id or user.has_role(Role.CONTENT_MANAGER)))
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "המתכון לא נמצא")

    if recipe.status == RecipeStatus.PUBLISHED:
        recipe.view_count += 1
        db.commit()
    return to_detail(recipe, servings)
