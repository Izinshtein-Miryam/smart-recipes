from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import AIFeature, Role


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    display_name: str
    role: Role
    is_active: bool
    created_at: datetime


class CreateContentManagerIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)


class UserPatch(BaseModel):
    is_active: bool | None = None
    role: Literal[Role.USER, Role.CONTENT_MANAGER] | None = None


class FeatureStats(BaseModel):
    feature: AIFeature
    calls: int
    errors: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    avg_latency_ms: int


class PopularRecipe(BaseModel):
    id: int
    slug: str
    title: str
    view_count: int


class StatsOut(BaseModel):
    since: datetime
    ai_by_feature: list[FeatureStats]
    total_cost_usd: float
    popular_recipes: list[PopularRecipe]
    users_by_role: dict[str, int]
    recipes_by_status: dict[str, int]


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: int | None
    action: str
    entity_type: str
    entity_id: str | None
    details: dict[str, Any]
    created_at: datetime


class ImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipe_id: int
    origin: str
    prompt: str | None
    original_url: str | None
    processed_url: str | None
    url: str | None
    use_original: bool
    is_primary: bool
    approved: bool


class ApproveImageIn(BaseModel):
    use_original: bool = False
