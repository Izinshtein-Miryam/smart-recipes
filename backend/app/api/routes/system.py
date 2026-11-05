"""System-admin endpoints: users, settings, statistics and audit log."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.deps import DbSession, SysAdmin
from app.core.security import hash_password
from app.models import AICall, AuditLog, Recipe, RecipeStatus, Role, Setting, User
from app.schemas.recipe import Page
from app.schemas.system import (
    AIUsage,
    AuditEntry,
    ContentManagerCreate,
    PopularRecipe,
    Stats,
    SystemSettings,
    SystemSettingsUpdate,
    UserRow,
    UserUpdate,
)
from app.services.audit import record_audit

router = APIRouter(prefix="/system", tags=["system"])


def _get_target(db: Session, actor: User, user_id: int) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "המשתמש לא נמצא")
    if target.id == actor.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "אי אפשר לבצע פעולה זו על החשבון שלך")
    if target.role == Role.SYSADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "אי אפשר לשנות מנהל מערכת")
    return target


@router.get("/users", response_model=Page[UserRow], summary="רשימת משתמשים")
def list_users(
    user: SysAdmin,
    db: DbSession,
    q: Annotated[str | None, Query(max_length=100)] = None,
    role: Role | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> Page[UserRow]:
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    if q:
        stmt = stmt.where(User.email.contains(q.lower()) | User.display_name.contains(q))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(User.id).offset((page - 1) * page_size).limit(page_size)).all()
    return Page(
        items=[UserRow.model_validate(u) for u in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/users",
    response_model=UserRow,
    status_code=status.HTTP_201_CREATED,
    summary="יצירת חשבון מנהל תוכן",
)
def create_user(body: ContentManagerCreate, actor: SysAdmin, db: DbSession) -> User:
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "כתובת המייל כבר רשומה")
    new = User(
        email=email,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        role=body.role,
    )
    db.add(new)
    db.flush()
    record_audit(db, actor, "user.create", "user", new.id, {"email": email, "role": new.role})
    db.commit()
    return new


@router.patch("/users/{user_id}", response_model=UserRow, summary="עדכון או השבתת משתמש")
def update_user(user_id: int, body: UserUpdate, actor: SysAdmin, db: DbSession) -> User:
    target = _get_target(db, actor, user_id)
    changes = body.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in changes.items():
        setattr(target, key, value)
    record_audit(db, actor, "user.update", "user", target.id, changes)
    db.commit()
    return target


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="מחיקת משתמש")
def delete_user(user_id: int, actor: SysAdmin, db: DbSession) -> None:
    target = _get_target(db, actor, user_id)
    record_audit(db, actor, "user.delete", "user", target.id, {"email": target.email})
    # Mirror the ON DELETE SET NULL foreign keys explicitly, so this does not depend on
    # the database enforcing them (SQLite only does with PRAGMA foreign_keys=ON).
    for model, column in (
        (Recipe, "owner_id"),
        (AuditLog, "actor_id"),
        (AICall, "user_id"),
        (Setting, "updated_by"),
    ):
        db.execute(update(model).where(getattr(model, column) == target.id).values({column: None}))
    db.delete(target)
    db.commit()


def load_system_settings(db: Session) -> SystemSettings:
    """Stored values merged over the defaults."""
    stored = {row.key: row.value for row in db.scalars(select(Setting))}
    known = {k: v for k, v in stored.items() if k in SystemSettings.model_fields}
    return SystemSettings.model_validate(known)


@router.get("/settings", response_model=SystemSettings, summary="הגדרות מערכת")
def get_system_settings(user: SysAdmin, db: DbSession) -> SystemSettings:
    return load_system_settings(db)


@router.put("/settings", response_model=SystemSettings, summary="עדכון הגדרות מערכת")
def update_system_settings(
    body: SystemSettingsUpdate, actor: SysAdmin, db: DbSession
) -> SystemSettings:
    current = load_system_settings(db).model_dump(mode="json")
    changes = body.model_dump(mode="json", exclude_unset=True, exclude_none=True)
    for key, value in changes.items():
        row = db.get(Setting, key)
        if row is None:
            db.add(Setting(key=key, value=value, updated_by=actor.id))
        else:
            row.value = value
            row.updated_by = actor.id
        record_audit(
            db, actor, "settings.update", "setting", key, {"from": current[key], "to": value}
        )
    db.commit()
    return load_system_settings(db)


@router.get("/stats", response_model=Stats, summary="סטטיסטיקות שימוש ועלויות")
def get_stats(
    user: SysAdmin, db: DbSession, popular_limit: Annotated[int, Query(ge=1, le=50)] = 10
) -> Stats:
    usage = [
        AIUsage(
            feature=feature,
            calls=calls,
            input_tokens=int(tokens_in or 0),
            output_tokens=int(tokens_out or 0),
            cost_usd=float(cost or 0.0),
        )
        for feature, calls, tokens_in, tokens_out, cost in db.execute(
            select(
                AICall.feature,
                func.count(),
                func.sum(AICall.input_tokens),
                func.sum(AICall.output_tokens),
                func.sum(AICall.cost_usd),
            ).group_by(AICall.feature)
        )
    ]
    popular = db.scalars(
        select(Recipe)
        .where(Recipe.status == RecipeStatus.PUBLISHED)
        .order_by(Recipe.view_count.desc(), Recipe.id)
        .limit(popular_limit)
    ).all()
    return Stats(
        users=db.scalar(select(func.count()).select_from(User)) or 0,
        recipes=db.scalar(select(func.count()).select_from(Recipe)) or 0,
        ai_calls=sum(u.calls for u in usage),
        ai_cost_usd=sum(u.cost_usd for u in usage),
        ai_usage=usage,
        popular_recipes=[
            PopularRecipe(id=r.id, slug=r.slug, title=r.title, view_count=r.view_count)
            for r in popular
        ],
    )


@router.get("/audit", response_model=Page[AuditEntry], summary="יומן פעולות")
def get_audit(
    user: SysAdmin,
    db: DbSession,
    action: Annotated[str | None, Query(max_length=50)] = None,
    entity_type: Annotated[str | None, Query(max_length=50)] = None,
    actor_id: int | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> Page[AuditEntry]:
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if actor_id is not None:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(AuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return Page(
        items=[AuditEntry.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
