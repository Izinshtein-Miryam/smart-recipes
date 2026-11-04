"""FastAPI dependencies: DB session, current user and role guards."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.providers import (
    get_embedding_provider,
    get_image_provider,
    get_llm_client,
    get_rate_limiter,
)
from app.core.security import decode_access_token
from app.db import get_db
from app.models import Role, User
from app.services.ai.client import LLMClient
from app.services.embeddings.provider import EmbeddingProvider
from app.services.images.provider import ImageProvider
from app.services.limits import RateLimiter
from app.services.system_settings import get_system_settings

DbSession = Annotated[Session, Depends(get_db)]


def get_optional_user(request: Request, db: DbSession) -> User | None:
    token = request.cookies.get(get_settings().cookie_name)
    if not token:
        return None
    user_id = decode_access_token(token)
    if user_id is None:
        return None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user


OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def get_current_user(user: OptionalUser) -> User:
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "נדרשת התחברות")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(minimum: Role) -> Callable[[User], User]:
    def guard(user: CurrentUser) -> User:
        if not user.has_role(minimum):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "אין הרשאה")
        return user

    return guard


ContentManager = Annotated[User, Depends(require_role(Role.CONTENT_MANAGER))]
SysAdmin = Annotated[User, Depends(require_role(Role.SYSADMIN))]


def client_key(request: Request, user: OptionalUser) -> str:
    """Identity used for rate limits and quotas: the user id, or the client IP for guests."""
    if user is not None:
        return f"user:{user.id}"
    host = request.client.host if request.client else "unknown"
    return f"ip:{host}"


ClientKey = Annotated[str, Depends(client_key)]


def ai_rate_limit(
    key: ClientKey,
    db: DbSession,
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> None:
    limit = get_system_settings(db).quotas.ai_requests_per_minute
    if not limiter.allow(key, limit):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "יותר מדי בקשות, נסו שוב בעוד דקה")


AIRateLimited = Depends(ai_rate_limit)
LLM = Annotated[LLMClient, Depends(get_llm_client)]
Images = Annotated[ImageProvider, Depends(get_image_provider)]
Embeddings = Annotated[EmbeddingProvider, Depends(get_embedding_provider)]
