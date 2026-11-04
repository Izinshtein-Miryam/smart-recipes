from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import String, cast, or_, select

from app.core.deps import ContentManager, DbSession
from app.models import Ingredient
from app.schemas.ingredient import IngredientIn, IngredientOut
from app.services.audit import log_action

router = APIRouter(tags=["ingredients"])


@router.get("/ingredients", response_model=list[IngredientOut], summary="חיפוש רכיבים")
def list_ingredients(
    db: DbSession,
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[Ingredient]:
    stmt = select(Ingredient).order_by(Ingredient.name).limit(limit)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(Ingredient.name.like(pattern), cast(Ingredient.aliases, String).like(pattern))
        )
    return list(db.scalars(stmt))


@router.post(
    "/admin/ingredients",
    response_model=IngredientOut,
    status_code=status.HTTP_201_CREATED,
    summary="הוספת רכיב לטבלה המרכזית",
)
def create_ingredient(body: IngredientIn, db: DbSession, user: ContentManager) -> Ingredient:
    if db.scalar(select(Ingredient).where(Ingredient.name == body.name.strip())):
        raise HTTPException(status.HTTP_409_CONFLICT, "הרכיב כבר קיים")
    ingredient = Ingredient(**{**body.model_dump(), "name": body.name.strip()})
    db.add(ingredient)
    db.flush()
    log_action(db, user, "ingredient.create", "ingredient", ingredient.id, {"name": body.name})
    db.commit()
    return ingredient
