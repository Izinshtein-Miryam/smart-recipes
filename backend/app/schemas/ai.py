from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.models import KosherType


class ChatMessageIn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatIn(BaseModel):
    """The whole (short) conversation; nothing is stored server-side."""

    messages: list[ChatMessageIn] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def _ends_with_user(self) -> "ChatIn":
        if self.messages[-1].role != "user":
            raise ValueError("last message must be from the user")
        return self


class GenerateIn(BaseModel):
    mode: Literal["ingredients", "free_text", "adapt"]
    ingredients: list[str] = Field(default_factory=list, max_length=30)
    servings: int | None = Field(default=None, ge=1, le=50)
    kosher_type: KosherType | None = None
    text: str | None = Field(default=None, max_length=500)
    recipe_slug: str | None = None
    variation: int = Field(default=0, ge=0, le=20, description="Increment for 'try again'")

    @model_validator(mode="after")
    def _mode_fields(self) -> "GenerateIn":
        if self.mode == "ingredients" and not self.ingredients:
            raise ValueError("ingredients mode requires ingredients")
        if self.mode == "free_text" and not self.text:
            raise ValueError("free_text mode requires text")
        if self.mode == "adapt" and not (self.recipe_slug and self.text):
            raise ValueError("adapt mode requires recipe_slug and text")
        return self


class SavedRecipeOut(BaseModel):
    slug: str
    id: int
