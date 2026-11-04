from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.serializers import to_card, to_cards
from app.core.deps import DbSession, OptionalUser
from app.models import Recipe, RecipeStatus, TimeTag
from app.schemas.recipe import RecipeCard
from app.services import recommendations
from app.services.system_settings import get_system_settings

router = APIRouter(tags=["recommendations"])

LOCAL_TZ = ZoneInfo("Asia/Jerusalem")


class HomeOut(BaseModel):
    context: TimeTag
    title: str
    featured: RecipeCard | None
    items: list[RecipeCard]


def _now(at: datetime | None) -> datetime:
    if at is None:
        return datetime.now(LOCAL_TZ)
    return at if at.tzinfo else at.replace(tzinfo=LOCAL_TZ)


@router.get("/recommendations/home", response_model=HomeOut, summary="מובחר + 4 לפי הקשר זמן")
def home(
    db: DbSession,
    user: OptionalUser,
    at: Annotated[datetime | None, Query(description="זמן לחישוב (ברירת מחדל: עכשיו)")] = None,
) -> HomeOut:
    weights = get_system_settings(db).recommendation_weights
    prefs = user.dietary_prefs if user else []
    ctx, scored = recommendations.home(db, _now(at), weights, prefs)
    cards = [to_card(s.recipe) for s in scored]
    return HomeOut(
        context=ctx.tag, title=ctx.title, featured=cards[0] if cards else None, items=cards[1:]
    )


@router.get(
    "/recipes/{recipe_id}/similar", response_model=list[RecipeCard], summary="מתכונים דומים"
)
def similar(
    recipe_id: int,
    db: DbSession,
    user: OptionalUser,
    any_type: Annotated[bool, Query(description="לא להגביל לאותו סוג בשרי/חלבי/פרווה")] = False,
) -> list[RecipeCard]:
    base = db.scalar(
        select(Recipe)
        .where(Recipe.id == recipe_id, Recipe.status == RecipeStatus.PUBLISHED)
        .options(selectinload(Recipe.ingredients))
    )
    if base is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "המתכון לא נמצא")
    weights = get_system_settings(db).recommendation_weights
    prefs = user.dietary_prefs if user else []
    scored = recommendations.similar(
        db, base, _now(None), weights, prefs, same_kosher_type=not any_type
    )
    return to_cards([s.recipe for s in scored])
