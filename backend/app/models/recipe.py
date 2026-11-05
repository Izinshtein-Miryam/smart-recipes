"""The `recipes` table. Ingredients and steps are JSONB, like the AI structured-output schema."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import Difficulty, Equipment, Kashrut, Lang, RecipeStatus


def pg_enum(enum_cls: type, name: str) -> ENUM:
    return ENUM(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


class Recipe(Base):
    __tablename__ = "recipes"
    __table_args__ = (
        Index("ix_recipes_status", "status"),
        Index("ix_recipes_kashrut", "kashrut"),
        Index("ix_recipes_difficulty", "difficulty"),
        Index("ix_recipes_prep_minutes", "prep_minutes"),
        Index("ix_recipes_equipment", "equipment", postgresql_using="gin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lang: Mapped[Lang] = mapped_column(pg_enum(Lang, "lang"))
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="")
    servings: Mapped[int] = mapped_column(Integer)
    prep_minutes: Mapped[int] = mapped_column(Integer)
    difficulty: Mapped[Difficulty] = mapped_column(pg_enum(Difficulty, "difficulty"))
    equipment: Mapped[list[Equipment]] = mapped_column(
        ARRAY(pg_enum(Equipment, "equipment")), server_default=text("'{}'")
    )
    kashrut: Mapped[Kashrut] = mapped_column(pg_enum(Kashrut, "kashrut"))
    ingredients: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    steps: Mapped[list[str]] = mapped_column(JSONB)
    nutrition: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    image_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[RecipeStatus] = mapped_column(
        pg_enum(RecipeStatus, "recipe_status"),
        default=RecipeStatus.PENDING,
        server_default=RecipeStatus.PENDING.value,
    )
    source_recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="SET NULL"), nullable=True
    )
    submitter_ip_hash: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def image_url(self) -> str | None:
        """Public URL; pending/rejected images are never served."""
        if self.image_path and self.image_path.startswith("public/"):
            return "/media/" + self.image_path.removeprefix("public/")
        return None
