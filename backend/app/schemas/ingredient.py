from pydantic import BaseModel, ConfigDict, Field

from app.models import KosherType


class IngredientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    aliases: list[str]
    category: str
    kosher_type: KosherType
    is_basic: bool
    default_unit: str | None


class IngredientIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    aliases: list[str] = Field(default_factory=list)
    category: str = Field(min_length=1, max_length=50)
    kosher_type: KosherType
    is_basic: bool = False
    default_unit: str | None = Field(default=None, max_length=30)
