from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import case, func, or_, select

from app.core.deps import DbSession, SysAdmin
from app.core.security import hash_password
from app.models import AICall, AuditLog, Recipe, Role, User
from app.schemas.recipe import Page
from app.schemas.system import (
    AdminUserOut,
    AuditOut,
    CreateContentManagerIn,
    FeatureStats,
    PopularRecipe,
    StatsOut,
    UserPatch,
)
from app.services.audit import log_action
from app.services.system_settings import (
    SystemSettings,
    get_system_settings,
    update_system_settings,
)

router = APIRouter(prefix="/system", tags=["system"])


# ---- Users -------------------------------------------------------------------


@router.get("/users", response_model=list[AdminUserOut], summary="רשימת משתמשים")
def list_users(
    db: DbSession,
    admin: SysAdmin,
    q: Annotated[str | None, Query(max_length=100)] = None,
    role: Role | None = None,
) -> list[User]:
    stmt = select(User).order_by(User.created_at.desc())
    if q:
        stmt = stmt.where(or_(User.email.like(f"%{q}%"), User.display_name.like(f"%{q}%")))
    if role:
        stmt = stmt.where(User.role == role)
    return list(db.scalars(stmt))


@router.post(
    "/users",
    response_model=AdminUserOut,
    status_code=status.HTTP_201_CREATED,
    summary="יצירת מנהל תוכן",
)
def create_content_manager(body: CreateContentManagerIn, db: DbSession, admin: SysAdmin) -> User:
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "כתובת המייל כבר רשומה")
    user = User(
        email=email,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        role=Role.CONTENT_MANAGER,
    )
    db.add(user)
    db.flush()
    log_action(db, admin, "user.create", "user", user.id, {"role": Role.CONTENT_MANAGER})
    db.commit()
    return user


def _editable(db: DbSession, admin: User, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "המשתמש לא נמצא")
    if user.id == admin.id or user.role == Role.SYSADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "לא ניתן לשנות חשבון מנהל מערכת")
    return user


@router.patch("/users/{user_id}", response_model=AdminUserOut, summary="השבתה או שינוי תפקיד")
def patch_user(user_id: int, body: UserPatch, db: DbSession, admin: SysAdmin) -> User:
    user = _editable(db, admin, user_id)
    changes = body.model_dump(exclude_none=True)
    for key, value in changes.items():
        setattr(user, key, value)
    log_action(db, admin, "user.update", "user", user.id, changes)
    db.commit()
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="מחיקת משתמש")
def delete_user(user_id: int, db: DbSession, admin: SysAdmin) -> Response:
    user = _editable(db, admin, user_id)
    log_action(db, admin, "user.delete", "user", user.id, {"email": user.email})
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---- Settings ----------------------------------------------------------------


@router.get("/settings", response_model=SystemSettings, summary="הגדרות מערכת")
def get_settings_(db: DbSession, admin: SysAdmin) -> SystemSettings:
    return get_system_settings(db)


@router.put("/settings", response_model=SystemSettings, summary="עדכון הגדרות מערכת")
def put_settings(body: SystemSettings, db: DbSession, admin: SysAdmin) -> SystemSettings:
    result = update_system_settings(db, body, admin)
    log_action(db, admin, "settings.update", "settings", "system", body.model_dump())
    db.commit()
    return result


# ---- Stats & audit -----------------------------------------------------------


@router.get("/stats", response_model=StatsOut, summary="סטטיסטיקות שימוש ועלויות")
def stats(
    db: DbSession, admin: SysAdmin, days: Annotated[int, Query(ge=1, le=365)] = 1
) -> StatsOut:
    since = datetime.now(UTC) - timedelta(days=days)
    rows = db.execute(
        select(
            AICall.feature,
            func.count(AICall.id),
            func.sum(case((AICall.status != "ok", 1), else_=0)),
            func.sum(AICall.input_tokens),
            func.sum(AICall.output_tokens),
            func.sum(AICall.cost_usd),
            func.avg(AICall.latency_ms),
        )
        .where(AICall.created_at >= since)
        .group_by(AICall.feature)
    ).all()
    features = [
        FeatureStats(
            feature=r[0],
            calls=r[1],
            errors=r[2] or 0,
            input_tokens=r[3] or 0,
            output_tokens=r[4] or 0,
            cost_usd=round(r[5] or 0.0, 4),
            avg_latency_ms=int(r[6] or 0),
        )
        for r in rows
    ]
    popular = db.scalars(select(Recipe).order_by(Recipe.view_count.desc()).limit(10))
    users_by_role = dict(db.execute(select(User.role, func.count()).group_by(User.role)).all())
    by_status = dict(db.execute(select(Recipe.status, func.count()).group_by(Recipe.status)).all())
    return StatsOut(
        since=since,
        ai_by_feature=features,
        total_cost_usd=round(sum(f.cost_usd for f in features), 4),
        popular_recipes=[
            PopularRecipe(id=r.id, slug=r.slug, title=r.title, view_count=r.view_count)
            for r in popular
        ],
        users_by_role={str(k): v for k, v in users_by_role.items()},
        recipes_by_status={str(k): v for k, v in by_status.items()},
    )


@router.get("/audit", response_model=Page[AuditOut], summary="יומן פעולות")
def audit(
    db: DbSession,
    admin: SysAdmin,
    action: str | None = None,
    entity_type: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> Page[AuditOut]:
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(AuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    return Page(
        items=[AuditOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
