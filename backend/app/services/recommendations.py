"""Home-page (time context) and similar-recipe recommendations. Runs locally, no AI calls."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.domain.similarity import jaccard
from app.domain.time_context import TimeContext, time_context, time_match
from app.models import Recipe
from app.services.catalog import published
from app.services.embeddings.provider import cosine, from_blob
from app.services.system_settings import RecommendationWeights


@dataclass(frozen=True)
class Scored:
    recipe: Recipe
    score: float


def _diet_ok(recipe: Recipe, prefs: list[str]) -> bool:
    return all(p in recipe.diet_tags for p in prefs)


def _max_views(db: Session) -> int:
    return db.scalar(select(func.max(Recipe.view_count))) or 0


def _popularity(recipe: Recipe, max_views: int) -> float:
    return recipe.view_count / max_views if max_views else 0.0


def _time(ctx: TimeContext, r: Recipe) -> float:
    return time_match(ctx.tag, r.time_tags, r.total_minutes, r.difficulty, r.dish_type)


def _load(db: Session) -> list[Recipe]:
    stmt = published().options(selectinload(Recipe.images), selectinload(Recipe.ingredients))
    return list(db.scalars(stmt))


def home(
    db: Session, now: datetime, weights: RecommendationWeights, diet_prefs: list[str]
) -> tuple[TimeContext, list[Scored]]:
    ctx = time_context(now)
    max_views = _max_views(db)
    scored = [
        Scored(r, weights.time * _time(ctx, r) + weights.popularity * _popularity(r, max_views))
        for r in _load(db)
        if _diet_ok(r, diet_prefs)
    ]
    scored.sort(key=lambda s: (-s.score, s.recipe.id))
    return ctx, scored[:5]


def content_similarity(a: Recipe, b: Recipe) -> float:
    """Embedding cosine combined with ingredient and tag overlap, in [0, 1]."""
    emb = (
        max(0.0, cosine(from_blob(a.embedding), from_blob(b.embedding)))
        if a.embedding and b.embedding
        else 0.0
    )
    ingredients = jaccard(
        (i.ingredient_id for i in a.ingredients), (i.ingredient_id for i in b.ingredients)
    )
    tags = jaccard(
        [*a.diet_tags, *a.time_tags, a.dish_type], [*b.diet_tags, *b.time_tags, b.dish_type]
    )
    return 0.5 * emb + 0.3 * ingredients + 0.2 * tags


def similar(
    db: Session,
    base: Recipe,
    now: datetime,
    weights: RecommendationWeights,
    diet_prefs: list[str],
    same_kosher_type: bool = True,
    limit: int = 4,
) -> list[Scored]:
    ctx = time_context(now)
    max_views = _max_views(db)
    scored: list[Scored] = []
    for r in _load(db):
        if r.id == base.id or not _diet_ok(r, diet_prefs):
            continue
        if same_kosher_type and r.kosher_type != base.kosher_type:
            continue
        score = (
            weights.similarity * content_similarity(base, r)
            + weights.time * _time(ctx, r)
            + weights.popularity * _popularity(r, max_views)
        )
        scored.append(Scored(r, score))
    scored.sort(key=lambda s: (-s.score, s.recipe.id))
    return scored[:limit]
