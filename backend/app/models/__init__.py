"""ORM models. Importing this package registers all tables on `Base.metadata`."""

from app.models.enums import (
    AIFeature,
    Difficulty,
    DishType,
    ImageOrigin,
    KosherType,
    RecipeSource,
    RecipeStatus,
    Role,
    TimeTag,
)
from app.models.ingredient import Ingredient
from app.models.recipe import Recipe, RecipeImage, RecipeIngredient, RecipeStep
from app.models.system import AICall, AuditLog, Setting
from app.models.user import User
from app.models.user_data import Favorite, ShoppingListItem

__all__ = [
    "AICall",
    "AIFeature",
    "AuditLog",
    "Difficulty",
    "DishType",
    "Favorite",
    "ImageOrigin",
    "Ingredient",
    "KosherType",
    "Recipe",
    "RecipeImage",
    "RecipeIngredient",
    "RecipeSource",
    "RecipeStatus",
    "RecipeStep",
    "Role",
    "Setting",
    "ShoppingListItem",
    "TimeTag",
    "User",
]
