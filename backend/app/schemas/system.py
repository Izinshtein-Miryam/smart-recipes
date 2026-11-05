from datetime import datetime
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models import AIFeature, Role


class UserRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    display_name: str
    role: Role
    is_active: bool
    created_at: datetime


class ContentManagerCreate(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=8, max_length=128)]
    display_name: Annotated[str, Field(min_length=1, max_length=100)]
    role: Literal[Role.CONTENT_MANAGER] = Role.CONTENT_MANAGER


class UserUpdate(BaseModel):
    display_name: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    is_active: bool | None = None


class RecommendationWeights(BaseModel):
    similarity: Annotated[float, Field(ge=0, le=1)] = 0.6
    time: Annotated[float, Field(ge=0, le=1)] = 0.3
    popularity: Annotated[float, Field(ge=0, le=1)] = 0.1

    @model_validator(mode="after")
    def _sum_to_one(self) -> Self:
        if abs(self.similarity + self.time + self.popularity - 1.0) > 0.001:
            raise ValueError("סכום המשקלות חייב להיות 1")
        return self


class SystemSettings(BaseModel):
    guest_daily_quota: Annotated[int, Field(ge=0, le=1000)] = 3
    user_daily_quota: Annotated[int, Field(ge=0, le=1000)] = 20
    recommendation_weights: RecommendationWeights = RecommendationWeights()


class SystemSettingsUpdate(BaseModel):
    """Partial update: omitted keys keep their current value."""

    guest_daily_quota: Annotated[int, Field(ge=0, le=1000)] | None = None
    user_daily_quota: Annotated[int, Field(ge=0, le=1000)] | None = None
    recommendation_weights: RecommendationWeights | None = None


class AIUsage(BaseModel):
    feature: AIFeature
    calls: int
    input_tokens: int
    output_tokens: int
    cost_usd: float


class PopularRecipe(BaseModel):
    id: int
    slug: str
    title: str
    view_count: int


class Stats(BaseModel):
    users: int
    recipes: int
    ai_calls: int
    ai_cost_usd: float
    ai_usage: list[AIUsage]
    popular_recipes: list[PopularRecipe]


class AuditEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: int | None
    action: str
    entity_type: str
    entity_id: str | None
    details: dict[str, Any]
    created_at: datetime
