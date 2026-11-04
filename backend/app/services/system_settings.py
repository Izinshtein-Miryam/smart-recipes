"""System settings stored in the `settings` table, with typed defaults."""

from typing import Any

from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.models import Setting, User

SETTINGS_KEY = "system"


class Quotas(BaseModel):
    guest_daily_generations: int = Field(3, ge=0)
    user_daily_generations: int = Field(20, ge=0)
    ai_requests_per_minute: int = Field(10, ge=1)


class RecommendationWeights(BaseModel):
    similarity: float = Field(0.6, ge=0)
    time: float = Field(0.3, ge=0)
    popularity: float = Field(0.1, ge=0)

    @model_validator(mode="after")
    def _not_all_zero(self) -> "RecommendationWeights":
        if self.similarity + self.time + self.popularity == 0:
            raise ValueError("at least one weight must be positive")
        return self


DEFAULT_BASIC_INGREDIENTS = [
    "מלח",
    "פלפל שחור",
    "שמן",
    "שמן זית",
    "מים",
    "סוכר",
    "פפריקה",
    "כמון",
    "כורכום",
    "אורגנו",
    "קינמון",
    "אבקת שום",
]


class SystemSettings(BaseModel):
    quotas: Quotas = Quotas()
    recommendation_weights: RecommendationWeights = RecommendationWeights()
    basic_ingredients: list[str] = Field(default_factory=lambda: list(DEFAULT_BASIC_INGREDIENTS))


def get_system_settings(db: Session) -> SystemSettings:
    row = db.get(Setting, SETTINGS_KEY)
    if row is None:
        return SystemSettings()
    return SystemSettings.model_validate(row.value)


def update_system_settings(db: Session, new: SystemSettings, actor: User) -> SystemSettings:
    value: dict[str, Any] = new.model_dump()
    row = db.get(Setting, SETTINGS_KEY)
    if row is None:
        db.add(Setting(key=SETTINGS_KEY, value=value, updated_by=actor.id))
    else:
        row.value = value
        row.updated_by = actor.id
    return new
