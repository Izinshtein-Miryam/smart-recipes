from pydantic import BaseModel

from app.schemas.recipe import RecipeCard


class FavoritesList(BaseModel):
    items: list[RecipeCard]
