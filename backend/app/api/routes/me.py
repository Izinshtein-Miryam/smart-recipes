from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.serializers import to_cards
from app.core.deps import CurrentUser, DbSession
from app.models import Recipe, User
from app.schemas.auth import ProfilePatch, UserOut
from app.schemas.recipe import RecipeCard

router = APIRouter(prefix="/me", tags=["me"])


@router.patch("", response_model=UserOut, summary="עדכון פרופיל ומגבלות תזונה")
def update_profile(body: ProfilePatch, db: DbSession, user: CurrentUser) -> User:
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.dietary_prefs is not None:
        user.dietary_prefs = body.dietary_prefs
    db.commit()
    return user


@router.get("/recipes", response_model=list[RecipeCard], summary="המתכונים ששמרתי מהיצירה החכמה")
def my_recipes(db: DbSession, user: CurrentUser) -> list[RecipeCard]:
    recipes = db.scalars(
        select(Recipe)
        .where(Recipe.owner_id == user.id)
        .order_by(Recipe.created_at.desc())
        .options(selectinload(Recipe.images))
    )
    return to_cards(list(recipes))
