"""FastAPI dependencies: DB session, current user and role guards."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.security import decode_access_token
from app.db import get_db
from app.models import Role, User

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
