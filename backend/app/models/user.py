from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import utcnow
from app.models.enums import Role


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False), default=Role.USER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    dietary_prefs: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    def has_role(self, minimum: Role) -> bool:
        order: dict[Any, int] = {Role.USER: 0, Role.CONTENT_MANAGER: 1, Role.SYSADMIN: 2}
        return order[self.role] >= order[minimum]
