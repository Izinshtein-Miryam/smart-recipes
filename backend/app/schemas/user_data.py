from pydantic import BaseModel, ConfigDict, Field


class ShoppingItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingredient_id: int
    name: str
    category: str
    quantity: float | None
    unit: str | None
    source_recipe_ids: list[int]
    checked: bool


class AddRecipeToListIn(BaseModel):
    recipe_id: int
    servings: int | None = Field(default=None, ge=1, le=100)


class ShoppingItemPatch(BaseModel):
    checked: bool | None = None
    quantity: float | None = Field(default=None, gt=0)
