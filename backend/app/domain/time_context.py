"""Time-of-day / day-of-week context for home page recommendations."""

from dataclasses import dataclass
from datetime import datetime

from app.models.enums import DishType, TimeTag


@dataclass(frozen=True)
class TimeContext:
    tag: TimeTag
    title: str


def time_context(now: datetime) -> TimeContext:
    # Thursday (3) and Friday (4): cooking ahead and hosting.
    if now.weekday() in (3, 4):
        return TimeContext(TimeTag.MAKE_AHEAD, "להכנה מראש ולאירוח")
    if 5 <= now.hour < 11:
        return TimeContext(TimeTag.MORNING, "מתאים לארוחת בוקר")
    if 11 <= now.hour < 16:
        return TimeContext(TimeTag.NOON, "מתאים לארוחת צהריים")
    return TimeContext(TimeTag.EVENING, "מתאים לארוחת ערב")


def time_match(
    tag: TimeTag, time_tags: list[str], total_minutes: int, difficulty: str, dish_type: str
) -> float:
    """1.0 when the recipe is explicitly tagged for this time; partial credit by heuristics."""
    if tag in time_tags:
        return 1.0
    if tag == TimeTag.MORNING and total_minutes <= 20 and difficulty == "easy":
        return 0.5
    if tag == TimeTag.EVENING and dish_type == DishType.MAIN:
        return 0.5
    return 0.0
