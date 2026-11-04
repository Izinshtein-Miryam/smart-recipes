from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import utcnow
from app.models.enums import (
    Difficulty,
    DishType,
    ImageOrigin,
    KosherType,
    RecipeSource,
    RecipeStatus,
)
from app.models.ingredient import Ingredient


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    kosher_type: Mapped[KosherType] = mapped_column(Enum(KosherType, native_enum=False))
    dish_type: Mapped[DishType] = mapped_column(Enum(DishType, native_enum=False))
    prep_minutes: Mapped[int] = mapped_column(Integer, default=0)
    cook_minutes: Mapped[int] = mapped_column(Integer, default=0)
    difficulty: Mapped[Difficulty] = mapped_column(Enum(Difficulty, native_enum=False))
    servings: Mapped[int] = mapped_column(Integer, default=4)
    time_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    diet_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[RecipeStatus] = mapped_column(
        Enum(RecipeStatus, native_enum=False), default=RecipeStatus.DRAFT, index=True
    )
    source: Mapped[RecipeSource] = mapped_column(
        Enum(RecipeSource, native_enum=False), default=RecipeSource.ADMIN
    )
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", order_by="RecipeIngredient.order"
    )
    steps: Mapped[list["RecipeStep"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", order_by="RecipeStep.order"
    )
    images: Mapped[list["RecipeImage"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan"
    )

    @property
    def total_minutes(self) -> int:
        return self.prep_minutes + self.cook_minutes

    @property
    def image_url(self) -> str | None:
        """URL of the approved primary image, or None (AI recipes are shown with an icon)."""
        for image in self.images:
            if image.is_primary and image.approved:
                return image.url
        return None


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"))
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"))
    quantity: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(30))
    note: Mapped[str | None] = mapped_column(String(200))
    order: Mapped[int] = mapped_column(Integer, default=0)

    recipe: Mapped[Recipe] = relationship(back_populates="ingredients")
    ingredient: Mapped[Ingredient] = relationship()


class RecipeStep(Base):
    __tablename__ = "recipe_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"))
    order: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    timer_seconds: Mapped[int | None] = mapped_column(Integer)
    ingredient_ids: Mapped[list[int]] = mapped_column(JSON, default=list)

    recipe: Mapped[Recipe] = relationship(back_populates="steps")


class RecipeImage(Base):
    __tablename__ = "recipe_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"))
    original_path: Mapped[str | None] = mapped_column(String(500))
    processed_path: Mapped[str | None] = mapped_column(String(500))
    origin: Mapped[ImageOrigin] = mapped_column(Enum(ImageOrigin, native_enum=False))
    prompt: Mapped[str | None] = mapped_column(Text)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    # Which version is shown: the processed one (default) or the original upload.
    use_original: Mapped[bool] = mapped_column(Boolean, default=False)

    recipe: Mapped[Recipe] = relationship(back_populates="images")

    @property
    def selected_path(self) -> str | None:
        if self.use_original or self.processed_path is None:
            return self.original_path
        return self.processed_path

    @property
    def url(self) -> str | None:
        return f"/media/{self.selected_path}" if self.selected_path else None
