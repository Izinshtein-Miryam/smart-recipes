from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession
from app.domain.servings import scale_quantity
from app.models import Ingredient, Recipe, RecipeStatus, ShoppingListItem
from app.schemas.shopping import (
    ShoppingAddRequest,
    ShoppingItemOut,
    ShoppingItemPatch,
    ShoppingList,
)

router = APIRouter(prefix="/shopping-list", tags=["shopping-list"])


def _build_list(db: DbSession, user_id: int) -> ShoppingList:
    rows = db.execute(
        select(ShoppingListItem, Ingredient)
        .join(Ingredient, Ingredient.id == ShoppingListItem.ingredient_id)
        .where(ShoppingListItem.user_id == user_id)
        .order_by(Ingredient.category, Ingredient.name, ShoppingListItem.id)
    ).all()
    return ShoppingList(
        items=[
            ShoppingItemOut(
                id=item.id,
                ingredient_id=item.ingredient_id,
                name=ing.name,
                category=ing.category,
                quantity=item.quantity,
                unit=item.unit,
                source_recipe_ids=item.source_recipe_ids,
                checked=item.checked,
            )
            for item, ing in rows
        ]
    )


def _sum_quantities(a: float | None, b: float | None) -> float | None:
    if a is None:
        return b
    if b is None:
        return a
    return round(a + b, 2)


def _get_item(db: DbSession, user_id: int, item_id: int) -> ShoppingListItem:
    item = db.scalar(
        select(ShoppingListItem).where(
            ShoppingListItem.id == item_id, ShoppingListItem.user_id == user_id
        )
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "הפריט לא נמצא")
    return item


@router.get("", response_model=ShoppingList, summary="רשימת הקניות שלי")
def get_shopping_list(user: CurrentUser, db: DbSession) -> ShoppingList:
    return _build_list(db, user.id)


@router.post("", response_model=ShoppingList, summary="הוספת רכיבי מתכון לרשימה")
def add_recipe_to_list(body: ShoppingAddRequest, user: CurrentUser, db: DbSession) -> ShoppingList:
    recipe = db.scalar(
        select(Recipe)
        .where(Recipe.id == body.recipe_id, Recipe.status == RecipeStatus.PUBLISHED)
        .options(selectinload(Recipe.ingredients))
    )
    if recipe is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "המתכון לא נמצא")

    existing = db.scalars(select(ShoppingListItem).where(ShoppingListItem.user_id == user.id))
    by_key: dict[tuple[int, str | None], ShoppingListItem] = {
        (i.ingredient_id, i.unit): i for i in existing
    }
    target = body.servings or recipe.servings
    for line in recipe.ingredients:
        quantity = scale_quantity(line.quantity, recipe.servings, target)
        key = (line.ingredient_id, line.unit)
        item = by_key.get(key)
        if item is None:
            by_key[key] = ShoppingListItem(
                user_id=user.id,
                ingredient_id=line.ingredient_id,
                quantity=quantity,
                unit=line.unit,
                source_recipe_ids=[recipe.id],
                checked=False,
            )
            db.add(by_key[key])
            continue
        item.quantity = _sum_quantities(item.quantity, quantity)
        if recipe.id not in item.source_recipe_ids:
            item.source_recipe_ids = [*item.source_recipe_ids, recipe.id]
        item.checked = False  # more is needed, so it is no longer done
    db.commit()
    return _build_list(db, user.id)


@router.patch("/{item_id}", response_model=ShoppingList, summary="סימון פריט כנקנה")
def update_item(
    item_id: int, body: ShoppingItemPatch, user: CurrentUser, db: DbSession
) -> ShoppingList:
    item = _get_item(db, user.id, item_id)
    item.checked = body.checked
    db.commit()
    return _build_list(db, user.id)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="הסרת פריט")
def delete_item(item_id: int, user: CurrentUser, db: DbSession) -> Response:
    db.delete(_get_item(db, user.id, item_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT, summary="ניקוי הרשימה")
def clear_list(user: CurrentUser, db: DbSession) -> Response:
    db.execute(delete(ShoppingListItem).where(ShoppingListItem.user_id == user.id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
