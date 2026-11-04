from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession
from app.domain.servings import scale_quantity
from app.domain.units import normalize_quantity
from app.models import Ingredient, Recipe, RecipeIngredient, RecipeStatus, ShoppingListItem
from app.schemas.user_data import AddRecipeToListIn, ShoppingItemOut, ShoppingItemPatch

router = APIRouter(prefix="/shopping-list", tags=["shopping-list"])


def _items(db: DbSession, user_id: int) -> list[ShoppingItemOut]:
    rows = db.execute(
        select(ShoppingListItem, Ingredient)
        .join(Ingredient, Ingredient.id == ShoppingListItem.ingredient_id)
        .where(ShoppingListItem.user_id == user_id)
        .order_by(Ingredient.category, Ingredient.name, ShoppingListItem.id)
    ).all()
    return [
        ShoppingItemOut(
            id=item.id,
            ingredient_id=ing.id,
            name=ing.name,
            category=ing.category,
            quantity=item.quantity,
            unit=item.unit,
            source_recipe_ids=item.source_recipe_ids,
            checked=item.checked,
        )
        for item, ing in rows
    ]


@router.get("", response_model=list[ShoppingItemOut], summary="רשימת הקניות המאוחדת")
def get_list(db: DbSession, user: CurrentUser) -> list[ShoppingItemOut]:
    return _items(db, user.id)


@router.post("", response_model=list[ShoppingItemOut], summary="הוספת רכיבי מתכון לרשימה")
def add_recipe(body: AddRecipeToListIn, db: DbSession, user: CurrentUser) -> list[ShoppingItemOut]:
    recipe = db.scalar(
        select(Recipe)
        .where(Recipe.id == body.recipe_id)
        .options(selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient))
    )
    if recipe is None or (recipe.status != RecipeStatus.PUBLISHED and recipe.owner_id != user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "המתכון לא נמצא")

    existing = list(db.scalars(select(ShoppingListItem).where(ShoppingListItem.user_id == user.id)))
    target = body.servings or recipe.servings
    for line in recipe.ingredients:
        quantity, unit = normalize_quantity(
            scale_quantity(line.quantity, recipe.servings, target), line.unit
        )
        # Same ingredient + same (normalized) unit -> one line with summed quantity.
        match = next(
            (
                i
                for i in existing
                if i.ingredient_id == line.ingredient_id and i.unit == unit and not i.checked
            ),
            None,
        )
        if match:
            if quantity is not None:
                match.quantity = round((match.quantity or 0) + quantity, 2)
            if recipe.id not in match.source_recipe_ids:
                match.source_recipe_ids = [*match.source_recipe_ids, recipe.id]
        else:
            item = ShoppingListItem(
                user_id=user.id,
                ingredient_id=line.ingredient_id,
                quantity=quantity,
                unit=unit,
                source_recipe_ids=[recipe.id],
                checked=False,
            )
            db.add(item)
            existing.append(item)
    db.commit()
    return _items(db, user.id)


@router.patch("/{item_id}", response_model=ShoppingItemOut, summary="סימון V או שינוי כמות")
def patch_item(
    item_id: int, body: ShoppingItemPatch, db: DbSession, user: CurrentUser
) -> ShoppingItemOut:
    item = db.get(ShoppingListItem, item_id)
    if item is None or item.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "הפריט לא נמצא")
    if body.checked is not None:
        item.checked = body.checked
    if body.quantity is not None:
        item.quantity = body.quantity
    db.commit()
    return next(i for i in _items(db, user.id) if i.id == item_id)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="הסרת פריט")
def delete_item(item_id: int, db: DbSession, user: CurrentUser) -> Response:
    item = db.get(ShoppingListItem, item_id)
    if item is None or item.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "הפריט לא נמצא")
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT, summary="ניקוי כל הרשימה")
def clear_list(db: DbSession, user: CurrentUser) -> Response:
    db.execute(delete(ShoppingListItem).where(ShoppingListItem.user_id == user.id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
