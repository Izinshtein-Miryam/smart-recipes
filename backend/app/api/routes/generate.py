import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.serializers import SSE_HEADERS, sse, to_detail
from app.core.deps import (
    LLM,
    AIRateLimited,
    ClientKey,
    CurrentUser,
    DbSession,
    Embeddings,
    OptionalUser,
)
from app.models import (
    AIFeature,
    Ingredient,
    Recipe,
    RecipeIngredient,
    RecipeSource,
    RecipeStatus,
    Role,
    User,
)
from app.schemas.ai import GenerateIn, SavedRecipeOut
from app.services import recipe_writer
from app.services.ai.client import ChatMessage, LLMError
from app.services.ai.prompts import GENERATE_SYSTEM, GENERATED_RECIPE_SCHEMA
from app.services.ai.service import AIService
from app.services.audit import log_action
from app.services.generation import (
    GeneratedRecipe,
    GenerationRejectedError,
    generated_store,
    validate_generated,
)
from app.services.limits import record_usage, used_today
from app.services.system_settings import SystemSettings, get_system_settings

router = APIRouter(prefix="/generate", tags=["generate"])

KOSHER_HE = {"meat": "בשרי", "dairy": "חלבי", "parve": "פרווה"}


def daily_limit(user: User | None, settings: SystemSettings) -> int | None:
    if user is None:
        return settings.quotas.guest_daily_generations
    if user.has_role(Role.CONTENT_MANAGER):
        return None
    return settings.quotas.user_daily_generations


def _load_base(db: DbSession, slug: str, user: User | None) -> Recipe:
    recipe = db.scalar(
        select(Recipe)
        .where(Recipe.slug == slug)
        .options(
            selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient),
            selectinload(Recipe.steps),
            selectinload(Recipe.images),
        )
    )
    visible = recipe is not None and (
        recipe.status == RecipeStatus.PUBLISHED or (user is not None and user.id == recipe.owner_id)
    )
    if recipe is None or not visible:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "המתכון לא נמצא")
    return recipe


def build_prompt(body: GenerateIn, settings: SystemSettings, base: Recipe | None) -> str:
    parts: list[str] = []
    if body.mode == "ingredients":
        parts.append(f"צור מתכון שמבוסס על הרכיבים: {', '.join(body.ingredients)}.")
        parts.append(
            "מותר להוסיף רק רכיבי בסיס מהרשימה הבאה, ושום רכיב אחר: "
            + ", ".join(settings.basic_ingredients)
            + "."
        )
    elif body.mode == "free_text":
        parts.append(f"בקשת המשתמש: {body.text}")
    else:
        assert base is not None  # noqa: S101 - validated by GenerateIn
        detail = to_detail(base).model_dump(
            include={"title", "description", "servings", "ingredients", "steps", "diet_tags"},
            mode="json",
        )
        parts.append(f"התאם את המתכון הבא לפי הבקשה: {body.text}")
        parts.append("פרט ב-changes כל שינוי שעשית.")
        parts.append(json.dumps(detail, ensure_ascii=False))
    if body.servings:
        parts.append(f"מספר מנות: {body.servings}.")
    if body.kosher_type:
        parts.append(f"סוג המתכון: {KOSHER_HE[body.kosher_type]}.")
    if body.variation:
        parts.append(f"כתוב גרסה שונה מהותית מהקודמות (גרסה מס' {body.variation + 1}).")
    return "\n".join(parts)


@router.post(
    "",
    summary="יצירה חכמה (SSE)",
    response_class=StreamingResponse,
    dependencies=[AIRateLimited],
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def generate(
    body: GenerateIn, db: DbSession, user: OptionalUser, key: ClientKey, llm: LLM
) -> StreamingResponse:
    """Events: `attempt` {attempt}, `delta` {text}, `retry` {reason},
    then `done` {id, recipe, remaining} or `error` {message}."""
    settings = get_system_settings(db)
    limit = daily_limit(user, settings)
    used = used_today(db, key, AIFeature.GENERATE)
    if limit is not None and used >= limit:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "הגעתם למכסת היצירות היומית" + ("" if user else ". הירשמו כדי לקבל מכסה גדולה יותר"),
        )
    base = (
        _load_base(db, body.recipe_slug, user)
        if body.mode == "adapt" and body.recipe_slug
        else None
    )
    prompt = build_prompt(body, settings, base)
    ai = AIService(llm, db, user.id if user else None)

    async def events() -> AsyncIterator[str]:
        messages: list[ChatMessage] = [{"role": "user", "content": prompt}]
        for attempt in (1, 2):
            yield sse("attempt", {"attempt": attempt})
            buf = ""
            try:
                async for chunk in ai.stream(
                    AIFeature.GENERATE,
                    system=GENERATE_SYSTEM,
                    messages=messages,
                    json_schema=GENERATED_RECIPE_SCHEMA,
                    effort="medium",
                    max_tokens=16000,
                ):
                    if isinstance(chunk, str):
                        buf += chunk
                        yield sse("delta", {"text": chunk})
            except LLMError as e:
                yield sse("error", {"message": str(e)})
                return
            try:
                recipe = validate_generated(
                    db,
                    buf,
                    requested_kosher=body.kosher_type,
                    provided=body.ingredients if body.mode == "ingredients" else None,
                    basic_names=settings.basic_ingredients,
                )
            except GenerationRejectedError as e:
                if attempt == 2:
                    yield sse("error", {"message": "לא הצלחנו ליצור מתכון תקין. נסו לנסח מחדש."})
                    return
                yield sse("retry", {"reason": str(e)})
                messages = [
                    *messages,
                    {"role": "assistant", "content": buf},
                    {"role": "user", "content": f"המתכון נדחה: {e}. כתוב מתכון מלא ומתוקן."},
                ]
                continue

            record_usage(db, key, AIFeature.GENERATE)
            remaining = None if limit is None else max(0, limit - used - 1)
            yield sse(
                "done",
                {
                    "id": generated_store.add(recipe),
                    "recipe": recipe.model_dump(mode="json"),
                    "remaining": remaining,
                },
            )
            return

    return StreamingResponse(events(), media_type="text/event-stream", headers=SSE_HEADERS)


def _resolve_ingredients(db: DbSession, recipe: GeneratedRecipe) -> list[Ingredient]:
    """Map every generated ingredient to a row, creating unknown ones."""
    result: list[Ingredient] = []
    for item in recipe.ingredients:
        ing = db.get(Ingredient, item.ingredient_id) if item.ingredient_id else None
        ing = ing or recipe_writer.find_ingredient(db, item.name)
        if ing is None:
            ing = Ingredient(
                name=item.name.strip(),
                aliases=[],
                category="אחר",
                kosher_type=item.kosher_type,
                default_unit=item.unit,
            )
            db.add(ing)
            db.flush()
        result.append(ing)
    return result


@router.post("/{generated_id}/save", response_model=SavedRecipeOut, summary="שמירת מתכון שנוצר")
def save_generated(
    generated_id: str, db: DbSession, user: CurrentUser, embedder: Embeddings
) -> SavedRecipeOut:
    entry = generated_store.get(generated_id)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "המתכון שנוצר אינו זמין עוד, צרו אותו מחדש")
    if entry.saved_slug:
        existing = db.scalar(select(Recipe).where(Recipe.slug == entry.saved_slug))
        if existing:
            return SavedRecipeOut(slug=existing.slug, id=existing.id)

    g = entry.recipe
    ingredients = _resolve_ingredients(db, g)
    recipe = Recipe(
        title=g.title,
        slug=recipe_writer.new_slug("ai"),
        description=g.description,
        dish_type=g.dish_type,
        difficulty=g.difficulty,
        prep_minutes=g.prep_minutes,
        cook_minutes=g.cook_minutes,
        servings=g.servings,
        time_tags=[t.value for t in g.time_tags],
        diet_tags=g.diet_tags,
        status=RecipeStatus.DRAFT,
        source=RecipeSource.AI,
        owner_id=user.id,
    )
    try:
        recipe_writer.set_content(
            db,
            recipe,
            [
                recipe_writer.IngredientLineIn(ing.id, item.quantity, item.unit, item.note)
                for ing, item in zip(ingredients, g.ingredients, strict=True)
            ],
            [recipe_writer.StepIn(s.text, s.timer_seconds) for s in g.steps],
            embedder,
        )
    except recipe_writer.RecipeValidationError as e:  # pragma: no cover - validated earlier
        db.rollback()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from e
    db.add(recipe)
    db.flush()
    log_action(db, user, "recipe.save_generated", "recipe", recipe.id)
    db.commit()
    entry.saved_slug = recipe.slug
    return SavedRecipeOut(slug=recipe.slug, id=recipe.id)
