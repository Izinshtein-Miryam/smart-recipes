"""Kosher-type rules: meat/dairy mixing check and recipe type derivation."""

from collections.abc import Iterable

from app.models.enums import KosherType


class MeatDairyMixError(ValueError):
    """Raised when a recipe contains both meat and dairy ingredients."""


def derive_recipe_kosher_type(ingredient_types: Iterable[KosherType]) -> KosherType:
    """Return the recipe kosher type from its ingredients, or raise on a meat/dairy mix."""
    types = set(ingredient_types)
    has_meat = KosherType.MEAT in types
    has_dairy = KosherType.DAIRY in types
    if has_meat and has_dairy:
        raise MeatDairyMixError("המתכון מכיל גם רכיבים בשריים וגם רכיבים חלביים")
    if has_meat:
        return KosherType.MEAT
    if has_dairy:
        return KosherType.DAIRY
    return KosherType.PARVE
