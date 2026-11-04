from sqlalchemy import JSON, Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import KosherType


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list)
    category: Mapped[str] = mapped_column(String(50))
    kosher_type: Mapped[KosherType] = mapped_column(Enum(KosherType, native_enum=False))
    is_basic: Mapped[bool] = mapped_column(Boolean, default=False)
    default_unit: Mapped[str | None] = mapped_column(String(30))
