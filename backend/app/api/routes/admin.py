"""Content-manager endpoints: recipe management and recipe images."""

import io
import re
import shutil
import time
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.core.deps import ContentManager, DbSession
from app.domain.kosher import MeatDairyMixError, derive_recipe_kosher_type
from app.models import (
    AICall,
    AIFeature,
    ImageOrigin,
    Ingredient,
    Recipe,
    RecipeImage,
    RecipeIngredient,
    RecipeSource,
    RecipeStatus,
    RecipeStep,
)
from app.schemas.admin import (
    AdminIngredientLine,
    AdminRecipeDetail,
    AdminRecipeRow,
    AdminStep,
    ImageUpdate,
    RecipeImageOut,
    RecipeIn,
    StatusIn,
)
from app.schemas.recipe import Page
from app.services.audit import record_audit
from app.services.images.provider import ImageProvider, build_image_provider, to_webp

router = APIRouter(prefix="/admin", tags=["admin"])

MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
PUBLISH_REQUIRES = "פרסום מחייב לפחות רכיב אחד ושלב אחד"


def get_image_provider() -> ImageProvider:
    return build_image_provider(get_settings())


def get_media_dir() -> Path:
    return get_settings().media_dir


ImageProviderDep = Annotated[ImageProvider, Depends(get_image_provider)]
MediaDir = Annotated[Path, Depends(get_media_dir)]


def _slugify(title: str) -> str:
    slug = re.sub(r"[^\w]+", "-", title.strip().lower()).strip("-_")
    return slug or "recipe"


def _unique_slug(db: Session, title: str) -> str:
    base = _slugify(title)[:180]
    slug, n = base, 1
    while db.scalar(select(Recipe.id).where(Recipe.slug == slug)):
        n += 1
        slug = f"{base}-{n}"
    return slug


def _load(db: Session, recipe_id: int) -> Recipe:
    recipe = db.scalar(
        select(Recipe)
        .where(Recipe.id == recipe_id)
        .options(
            selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient),
            selectinload(Recipe.steps),
            selectinload(Recipe.images),
        )
    )
    if recipe is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "המתכון לא נמצא")
    return recipe


def _detail(recipe: Recipe) -> AdminRecipeDetail:
    return AdminRecipeDetail(
        **AdminRecipeRow.model_validate(recipe).model_dump(),
        description=recipe.description,
        prep_minutes=recipe.prep_minutes,
        cook_minutes=recipe.cook_minutes,
        servings=recipe.servings,
        time_tags=recipe.time_tags,
        diet_tags=recipe.diet_tags,
        ingredients=[
            AdminIngredientLine(
                ingredient_id=ri.ingredient_id,
                name=ri.ingredient.name,
                quantity=ri.quantity,
                unit=ri.unit,
                note=ri.note,
            )
            for ri in recipe.ingredients
        ],
        steps=[AdminStep.model_validate(s) for s in recipe.steps],
        images=[RecipeImageOut.model_validate(i) for i in recipe.images],
    )


def _apply(db: Session, recipe: Recipe, body: RecipeIn) -> None:
    ids = {line.ingredient_id for line in body.ingredients}
    found = {i.id: i for i in db.scalars(select(Ingredient).where(Ingredient.id.in_(ids)))}
    missing = ids - found.keys()
    if missing:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"רכיבים לא קיימים: {sorted(missing)}"
        )
    if body.status == RecipeStatus.PUBLISHED and not (body.ingredients and body.steps):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, PUBLISH_REQUIRES)
    try:
        kosher = derive_recipe_kosher_type(i.kosher_type for i in found.values())
    except MeatDairyMixError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    recipe.title = body.title
    recipe.description = body.description
    recipe.kosher_type = kosher
    recipe.dish_type = body.dish_type
    recipe.difficulty = body.difficulty
    recipe.prep_minutes = body.prep_minutes
    recipe.cook_minutes = body.cook_minutes
    recipe.servings = body.servings
    recipe.time_tags = body.time_tags
    recipe.diet_tags = body.diet_tags
    recipe.status = body.status
    recipe.ingredients = [
        RecipeIngredient(
            ingredient_id=line.ingredient_id,
            quantity=line.quantity,
            unit=line.unit,
            note=line.note,
            order=n,
        )
        for n, line in enumerate(body.ingredients)
    ]
    recipe.steps = [
        RecipeStep(
            order=n, text=s.text, timer_seconds=s.timer_seconds, ingredient_ids=s.ingredient_ids
        )
        for n, s in enumerate(body.steps, start=1)
    ]


@router.get("/recipes", response_model=Page[AdminRecipeRow], summary="טבלת מתכונים לניהול")
def list_recipes(
    user: ContentManager,
    db: DbSession,
    q: Annotated[str | None, Query(max_length=100)] = None,
    status_filter: Annotated[RecipeStatus | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 24,
) -> Page[AdminRecipeRow]:
    stmt = select(Recipe)
    if status_filter:
        stmt = stmt.where(Recipe.status == status_filter)
    if q:
        stmt = stmt.where(or_(Recipe.title.contains(q), Recipe.slug.contains(q)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Recipe.updated_at.desc(), Recipe.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(
        items=[AdminRecipeRow.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/recipes/{recipe_id}", response_model=AdminRecipeDetail, summary="מתכון לעריכה")
def get_recipe(recipe_id: int, user: ContentManager, db: DbSession) -> AdminRecipeDetail:
    return _detail(_load(db, recipe_id))


@router.post(
    "/recipes",
    response_model=AdminRecipeDetail,
    status_code=status.HTTP_201_CREATED,
    summary="יצירת מתכון (טיוטה או פרסום)",
)
def create_recipe(body: RecipeIn, user: ContentManager, db: DbSession) -> AdminRecipeDetail:
    recipe = Recipe(slug=_unique_slug(db, body.title), source=RecipeSource.ADMIN, owner_id=user.id)
    _apply(db, recipe, body)
    db.add(recipe)
    db.flush()
    record_audit(
        db,
        user,
        "recipe.create",
        "recipe",
        recipe.id,
        {"title": recipe.title, "status": body.status},
    )
    db.commit()
    return _detail(_load(db, recipe.id))


@router.put("/recipes/{recipe_id}", response_model=AdminRecipeDetail, summary="עריכת מתכון")
def update_recipe(
    recipe_id: int, body: RecipeIn, user: ContentManager, db: DbSession
) -> AdminRecipeDetail:
    recipe = _load(db, recipe_id)
    _apply(db, recipe, body)
    record_audit(
        db,
        user,
        "recipe.update",
        "recipe",
        recipe.id,
        {"title": recipe.title, "status": body.status},
    )
    db.commit()
    return _detail(_load(db, recipe.id))


@router.patch(
    "/recipes/{recipe_id}/status", response_model=AdminRecipeDetail, summary="פרסום או הסתרה"
)
def set_status(
    recipe_id: int, body: StatusIn, user: ContentManager, db: DbSession
) -> AdminRecipeDetail:
    recipe = _load(db, recipe_id)
    if body.status == RecipeStatus.PUBLISHED and not (recipe.ingredients and recipe.steps):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, PUBLISH_REQUIRES)
    previous = recipe.status
    recipe.status = body.status
    record_audit(
        db, user, "recipe.status", "recipe", recipe.id, {"from": previous, "to": body.status}
    )
    db.commit()
    return _detail(_load(db, recipe.id))


@router.delete(
    "/recipes/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT, summary="מחיקת מתכון"
)
def delete_recipe(recipe_id: int, user: ContentManager, db: DbSession, media: MediaDir) -> None:
    recipe = _load(db, recipe_id)
    record_audit(db, user, "recipe.delete", "recipe", recipe.id, {"title": recipe.title})
    db.delete(recipe)
    db.commit()
    shutil.rmtree(media / "recipes" / str(recipe_id), ignore_errors=True)


def _save_webp(media: Path, recipe_id: int, data: bytes) -> str:
    rel = Path("recipes") / str(recipe_id) / f"{uuid.uuid4().hex}.webp"
    target = media / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return rel.as_posix()


def _read_upload(file: UploadFile) -> bytes:
    data = file.file.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "הקובץ גדול מ-10MB")
    try:
        with Image.open(io.BytesIO(data)) as img:
            fmt = img.format
            img.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "קובץ תמונה לא תקין") from exc
    if fmt not in ALLOWED_IMAGE_FORMATS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "יש להעלות JPG, PNG או WebP")
    return data


def _default_prompt(recipe: Recipe) -> str:
    names = ", ".join(ri.ingredient.name for ri in recipe.ingredients)
    return f"{recipe.title}. {recipe.description} Ingredients: {names}".strip()


async def _run_provider(db: Session, call: Callable[[], Awaitable[bytes]]) -> bytes:
    start = time.perf_counter()
    model = get_settings().image_provider
    try:
        result = await call()
    except Exception as exc:
        _log_image_call(db, model, start, "error")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "עיבוד התמונה נכשל") from exc
    _log_image_call(db, model, start, "ok")
    return result


def _log_image_call(db: Session, model: str, start: float, call_status: str) -> None:
    db.add(
        AICall(
            feature=AIFeature.IMAGE,
            model=model,
            latency_ms=int((time.perf_counter() - start) * 1000),
            status=call_status,
        )
    )
    db.commit()


@router.post(
    "/recipes/{recipe_id}/images",
    response_model=RecipeImageOut,
    status_code=status.HTTP_201_CREATED,
    summary="העלאה, עיבוד או יצירה של תמונה",
)
async def add_image(
    recipe_id: int,
    user: ContentManager,
    db: DbSession,
    provider: ImageProviderDep,
    media: MediaDir,
    action: Annotated[Literal["upload", "edit", "generate"], Form()] = "upload",
    prompt: Annotated[str | None, Form(max_length=2000)] = None,
    file: Annotated[UploadFile | None, File()] = None,
) -> RecipeImage:
    recipe = _load(db, recipe_id)
    if action != "generate" and file is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "חסר קובץ תמונה")

    original_path: str | None = None
    processed_path: str | None = None
    origin = ImageOrigin.UPLOAD
    if action == "generate":
        origin = ImageOrigin.AI_GENERATE
        text = prompt or _default_prompt(recipe)
        generated = await _run_provider(db, lambda: provider.generate(text))
        processed_path = _save_webp(media, recipe_id, generated)
    elif file is not None:
        original = to_webp(_read_upload(file))
        original_path = _save_webp(media, recipe_id, original)
        if action == "edit":
            origin = ImageOrigin.AI_EDIT
            instructions = prompt or "Professional food photo"
            edited = await _run_provider(db, lambda: provider.edit(original, instructions))
            processed_path = _save_webp(media, recipe_id, edited)

    image = RecipeImage(
        recipe_id=recipe_id,
        original_path=original_path,
        processed_path=processed_path,
        origin=origin,
        prompt=prompt,
        is_primary=False,
        approved=False,
    )
    db.add(image)
    db.flush()
    record_audit(
        db, user, "image.create", "recipe", recipe_id, {"image_id": image.id, "origin": origin}
    )
    db.commit()
    return image


@router.patch(
    "/recipes/{recipe_id}/images/{image_id}",
    response_model=RecipeImageOut,
    summary="אישור תמונה או הגדרתה כראשית",
)
def update_image(
    recipe_id: int, image_id: int, body: ImageUpdate, user: ContentManager, db: DbSession
) -> RecipeImage:
    image = db.scalar(
        select(RecipeImage).where(RecipeImage.id == image_id, RecipeImage.recipe_id == recipe_id)
    )
    if image is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "התמונה לא נמצאה")
    if body.approved is not None:
        image.approved = body.approved
    if body.is_primary:
        if not image.approved:
            raise HTTPException(status.HTTP_409_CONFLICT, "יש לאשר את התמונה לפני הגדרתה כראשית")
        for other in db.scalars(select(RecipeImage).where(RecipeImage.recipe_id == recipe_id)):
            other.is_primary = other.id == image.id
    elif body.is_primary is False:
        image.is_primary = False
    if not image.approved:
        image.is_primary = False
    record_audit(
        db,
        user,
        "image.update",
        "recipe",
        recipe_id,
        {"image_id": image.id, "approved": image.approved, "is_primary": image.is_primary},
    )
    db.commit()
    return image
