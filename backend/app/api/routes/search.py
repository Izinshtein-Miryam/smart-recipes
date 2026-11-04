import json
import logging
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import ValidationError
from sqlalchemy import select

from app.api.serializers import to_cards
from app.core.deps import LLM, AIRateLimited, DbSession, OptionalUser
from app.models import AIFeature, Ingredient, Recipe, RecipeStatus
from app.schemas.search import (
    FiltersModel,
    RelaxationOut,
    SmartSearchIn,
    SmartSearchOut,
    Suggestion,
)
from app.services import catalog
from app.services.ai.client import LLMError
from app.services.ai.prompts import FILTERS_SCHEMA, SMART_SEARCH_SYSTEM
from app.services.ai.service import AIService

router = APIRouter(prefix="/search", tags=["search"])
log = logging.getLogger(__name__)

# Category suggestions: label -> list-endpoint query string.
CATEGORIES: dict[str, str] = {
    "בשרי": "kosher_type=meat",
    "חלבי": "kosher_type=dairy",
    "פרווה": "kosher_type=parve",
    "מנה ראשונה": "dish_type=starter",
    "מנה עיקרית": "dish_type=main",
    "תוספת": "dish_type=side",
    "קינוח": "dish_type=dessert",
    "מאפה": "dish_type=baked",
    "ללא גלוטן": "diet=gluten_free",
    "ללא סוכר": "diet=sugar_free",
    "ללא אגוזים": "diet=nut_free",
}
MAX_SUGGESTIONS = 8


def _rank(label: str, q: str) -> int:
    return 0 if label.startswith(q) else 1


@router.get("/suggest", response_model=list[Suggestion], summary="השלמה אוטומטית (מקומי, ללא AI)")
def suggest(
    db: DbSession, q: Annotated[str, Query(min_length=1, max_length=50)]
) -> list[Suggestion]:
    q = q.strip()
    pattern = f"%{q}%"
    out: list[tuple[int, Suggestion]] = []

    for slug, title in db.execute(
        select(Recipe.slug, Recipe.title).where(
            Recipe.status == RecipeStatus.PUBLISHED, Recipe.title.like(pattern)
        )
    ):
        out.append((_rank(title, q), Suggestion(type="recipe", label=title, value=slug)))

    for ing in db.scalars(select(Ingredient)):
        names = [ing.name, *ing.aliases]
        hit = next((n for n in names if q in n), None)
        if hit:
            out.append(
                (_rank(hit, q), Suggestion(type="ingredient", label=ing.name, value=ing.name))
            )

    for label, query in CATEGORIES.items():
        if q in label:
            out.append((_rank(label, q), Suggestion(type="category", label=label, value=query)))

    out.sort(key=lambda pair: (pair[0], len(pair[1].label)))
    return [s for _, s in out[:MAX_SUGGESTIONS]]


@router.post(
    "/smart",
    response_model=SmartSearchOut,
    summary="משפט חופשי ← מסננים + תוצאות + הצעות ריכוך",
    dependencies=[AIRateLimited],
)
async def smart_search(
    body: SmartSearchIn, db: DbSession, user: OptionalUser, llm: LLM
) -> SmartSearchOut:
    fallback = False
    try:
        result = await AIService(llm, db, user.id if user else None).complete(
            AIFeature.SEARCH,
            system=SMART_SEARCH_SYSTEM,
            messages=[{"role": "user", "content": body.query}],
            json_schema=FILTERS_SCHEMA,
            effort="low",
            max_tokens=2000,
        )
        filters_model = FiltersModel.model_validate(json.loads(result.text))
    except (LLMError, json.JSONDecodeError, ValidationError) as e:
        # The AI only interprets; when it is unavailable fall back to plain text search.
        log.warning("smart search fell back to text search: %s", e)
        fallback = True
        filters_model = FiltersModel(text=body.query)

    filters = filters_model.to_filters()
    results = catalog.search(db, filters)
    total = catalog.count(db, filters)
    if fallback and total == 0:
        # Plain text search over the whole sentence rarely matches; try each word.
        words = [w for w in body.query.split() if len(w) > 1]
        seen: dict[int, Recipe] = {}
        for word in words:
            for r in catalog.search(db, catalog.RecipeFilters(text=word)):
                seen.setdefault(r.id, r)
        results = list(seen.values())[:24]
        total = len(seen)

    relax = [] if total else catalog.relaxations(db, filters)
    return SmartSearchOut(
        query=body.query,
        filters=filters_model,
        results=to_cards(results),
        total=total,
        relaxations=[
            RelaxationOut(remove=r.remove, count=r.count, message=r.message) for r in relax
        ],
        fallback=fallback,
    )
