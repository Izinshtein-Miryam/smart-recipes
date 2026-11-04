"""Rate limiting (per minute, in memory) and daily quotas (persisted) for AI features."""

import time
from collections import defaultdict, deque
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AIFeature, QuotaUsage


class RateLimiter:
    """Sliding-window limiter. Process-local, which is fine for a single local server."""

    def __init__(self, window_seconds: float = 60.0) -> None:
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int) -> bool:
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] >= self.window:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(now)
        return True

    def reset(self) -> None:
        self._hits.clear()


def _start_of_day() -> datetime:
    now = datetime.now(UTC)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def used_today(db: Session, client_key: str, feature: AIFeature) -> int:
    stmt = select(func.count(QuotaUsage.id)).where(
        QuotaUsage.client_key == client_key,
        QuotaUsage.feature == feature,
        QuotaUsage.created_at >= _start_of_day(),
    )
    return db.scalar(stmt) or 0


def record_usage(db: Session, client_key: str, feature: AIFeature) -> None:
    db.add(QuotaUsage(client_key=client_key, feature=feature))
    db.commit()
