"""FastAPI dependencies: DB session, admin guard and the AI service."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.security import is_valid_admin_token
from app.db import get_db
from app.services.ai_service import AiService

DbSession = Annotated[Session, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False)


def require_admin(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> None:
    if credentials is None or not is_valid_admin_token(credentials.credentials):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")


AdminOnly = Depends(require_admin)


@lru_cache
def get_ai_service() -> AiService:
    return AiService.from_settings(get_settings())


AiDep = Annotated[AiService, Depends(get_ai_service)]
