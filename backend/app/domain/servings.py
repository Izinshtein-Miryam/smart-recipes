"""Pure serving-size scaling, used by the chat `scale_servings` tool (no AI involved)."""

from typing import Any


def scale_ingredients(
    ingredients: list[dict[str, Any]], from_servings: int, to_servings: int
) -> list[dict[str, Any]]:
    if from_servings < 1 or to_servings < 1:
        raise ValueError("servings must be positive")
    factor = to_servings / from_servings
    scaled = []
    for item in ingredients:
        quantity = item.get("quantity")
        scaled.append(
            {**item, "quantity": None if quantity is None else round(quantity * factor, 2)}
        )
    return scaled
