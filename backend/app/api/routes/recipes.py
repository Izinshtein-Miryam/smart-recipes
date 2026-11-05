"""Public recipe endpoints: browse approved recipes and submit new ones (pending approval)."""

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Query, Request, Response, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import func, select

from app.config import get_settings
from app.core.deps import DbSession
from app.domain.servings import scale_ingredients
from app.models import Difficulty, Equipment, Kashrut, Lang, Recipe, RecipeStatus
from app.schemas.recipe import Ingredient, RecipeCreate, RecipeOut, RecipeSummary
from app.services import storage

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("", response_model=list[RecipeSummary])
def list_recipes(
    response: Response,
    db: DbSession,
    lang: Lang | None = None,
    max_minutes: Annotated[int | None, Query(ge=1)] = None,
    difficulty: Difficulty | None = None,
    equipment: Annotated[list[Equipment] | None, Query()] = None,
    servings: Annotated[int | None, Query(ge=1)] = None,
    kashrut: Kashrut | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Recipe]:
    stmt = select(Recipe).where(Recipe.status == RecipeStatus.APPROVED)
    if lang:
        stmt = stmt.where(Recipe.lang == lang)
    if max_minutes:
        stmt = stmt.where(Recipe.prep_minutes <= max_minutes)
    if difficulty:
        stmt = stmt.where(Recipe.difficulty == difficulty)
    if equipment:
        stmt = stmt.where(Recipe.equipment.contains(equipment))
    if servings:
        stmt = stmt.where(Recipe.servings == servings)
    if kashrut:
        stmt = stmt.where(Recipe.kashrut == kashrut)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(Recipe.title.ilike(like) | Recipe.description.ilike(like))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    response.headers["X-Total-Count"] = str(total)
    ordered = stmt.order_by(Recipe.approved_at.desc(), Recipe.id).limit(limit).offset(offset)
    return list(db.scalars(ordered))


@router.get("/{recipe_id}", response_model=RecipeOut)
def get_recipe(
    recipe_id: uuid.UUID,
    db: DbSession,
    servings: Annotated[int | None, Query(ge=1, le=100)] = None,
) -> RecipeOut:
    """With `servings`, ingredient quantities are scaled (nutrition stays per serving)."""
    recipe = db.get(Recipe, recipe_id)
    if recipe is None or recipe.status != RecipeStatus.APPROVED:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "recipe not found")
    out = RecipeOut.model_validate(recipe)
    if servings and servings != recipe.servings:
        out.ingredients = [
            Ingredient.model_validate(i)
            for i in scale_ingredients(recipe.ingredients, recipe.servings, servings)
        ]
        out.servings = servings
    return out


def _ip_hash(request: Request) -> str:
    ip = request.client.host if request.client else "unknown"
    salt = get_settings().jwt_secret
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()


@router.post("", response_model=RecipeOut, status_code=status.HTTP_201_CREATED)
async def submit_recipe(
    request: Request,
    db: DbSession,
    lang: Annotated[Lang, Form()],
    title: Annotated[str, Form()],
    servings: Annotated[int, Form()],
    prep_minutes: Annotated[int, Form()],
    difficulty: Annotated[Difficulty, Form()],
    kashrut: Annotated[Kashrut, Form()],
    ingredients: Annotated[str, Form(description="JSON array")],
    steps: Annotated[str, Form(description="JSON array of strings")],
    description: Annotated[str, Form()] = "",
    equipment: Annotated[list[Equipment] | None, Form()] = None,
    source_recipe_id: Annotated[uuid.UUID | None, Form()] = None,
    image: UploadFile | None = None,
) -> Recipe:
    settings = get_settings()
    ip_hash = _ip_hash(request)

    since = datetime.now(UTC) - timedelta(days=1)
    recent = db.query(Recipe).filter(
        Recipe.submitter_ip_hash == ip_hash, Recipe.created_at >= since
    )
    if recent.count() >= settings.max_submissions_per_day:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "daily submission limit reached")

    try:
        data = RecipeCreate.model_validate(
            {
                "lang": lang,
                "title": title,
                "description": description,
                "servings": servings,
                "prep_minutes": prep_minutes,
                "difficulty": difficulty,
                "kashrut": kashrut,
                "equipment": equipment or [],
                "ingredients": json.loads(ingredients),
                "steps": json.loads(steps),
                "source_recipe_id": source_recipe_id,
            }
        )
    except (ValidationError, json.JSONDecodeError) as exc:
        raise HTTPException(422, "invalid recipe data") from exc

    if data.source_recipe_id and db.get(Recipe, data.source_recipe_id) is None:
        raise HTTPException(422, "unknown source recipe")

    image_path = None
    if image is not None and image.filename:
        # Read one byte past the limit so oversize uploads are rejected without buffering them all.
        content = await image.read(settings.max_image_bytes + 1)
        try:
            image_path = storage.save_pending(content)
        except storage.ImageTooLargeError as exc:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, str(exc)) from exc
        except storage.InvalidImageError as exc:
            raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(exc)) from exc

    values = data.model_dump(mode="json", exclude={"ingredients", "steps"})
    recipe = Recipe(
        **{**values, "source_recipe_id": data.source_recipe_id},
        ingredients=[i.model_dump() for i in data.ingredients],
        steps=data.steps,
        image_path=image_path,
        submitter_ip_hash=ip_hash,
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe
