"""Audit log helper."""

from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def log_action(
    db: Session,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: int | str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Add an audit row to the session. The caller commits."""
    db.add(
        AuditLog(
            actor_id=actor.id if actor else None,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=details or {},
        )
    )
