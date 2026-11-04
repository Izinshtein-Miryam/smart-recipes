from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.serializers import to_cards
from app.core.deps import CurrentUser, DbSession
from app.models import Favorite, Recipe, RecipeStatus
from app.schemas.recipe import RecipeCard

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("", response_model=list[RecipeCard], summary="המועדפים שלי")
def list_favorites(db: DbSession, user: CurrentUser) -> list[RecipeCard]:
    recipes = db.scalars(
        select(Recipe)
        .join(Favorite, Favorite.recipe_id == Recipe.id)
        .where(Favorite.user_id == user.id, Recipe.status == RecipeStatus.PUBLISHED)
        .order_by(Favorite.created_at.desc())
        .options(selectinload(Recipe.images))
    )
    return to_cards(list(recipes))


@router.post("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT, summary="הוספה למועדפים")
def add_favorite(recipe_id: int, db: DbSession, user: CurrentUser) -> Response:
    recipe = db.get(Recipe, recipe_id)
    if recipe is None or recipe.status != RecipeStatus.PUBLISHED:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "המתכון לא נמצא")
    if db.get(Favorite, (user.id, recipe_id)) is None:
        db.add(Favorite(user_id=user.id, recipe_id=recipe_id))
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT, summary="הסרה מהמועדפים")
def remove_favorite(recipe_id: int, db: DbSession, user: CurrentUser) -> Response:
    favorite = db.get(Favorite, (user.id, recipe_id))
    if favorite is not None:
        db.delete(favorite)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
