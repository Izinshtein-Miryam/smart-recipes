import time
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status
from PIL import UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import AIRateLimited, ContentManager, DbSession, Images
from app.models import AICall, AIFeature, ImageOrigin, Recipe, RecipeImage, RecipeIngredient
from app.schemas.system import ApproveImageIn, ImageOut
from app.services.audit import log_action
from app.services.images.provider import ImageProvider, to_webp
from app.services.images.storage import delete_image, save_image

router = APIRouter(prefix="/admin", tags=["admin-images"])

MAX_BYTES = 10 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
ENHANCE_INSTRUCTIONS = (
    "Improve lighting, background and composition so the photo looks professional. "
    "Keep the dish itself unchanged."
)


def _out(image: RecipeImage) -> ImageOut:
    return ImageOut(
        id=image.id,
        recipe_id=image.recipe_id,
        origin=image.origin,
        prompt=image.prompt,
        original_url=f"/media/{image.original_path}" if image.original_path else None,
        processed_url=f"/media/{image.processed_path}" if image.processed_path else None,
        url=image.url,
        use_original=image.use_original,
        is_primary=image.is_primary,
        approved=image.approved,
    )


def _recipe(db: Session, recipe_id: int) -> Recipe:
    recipe = db.scalar(
        select(Recipe)
        .where(Recipe.id == recipe_id)
        .options(selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient))
    )
    if recipe is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "המתכון לא נמצא")
    return recipe


def default_prompt(recipe: Recipe) -> str:
    names = ", ".join(i.ingredient.name for i in recipe.ingredients[:8])
    return (
        f'Professional food photograph of the dish "{recipe.title}". '
        f"{recipe.description}. Main ingredients: {names}."
    )


async def _call_provider(
    db: Session,
    provider: ImageProvider,
    user_id: int,
    op: Literal["edit", "generate"],
    **kw: object,
) -> bytes:
    start = time.perf_counter()
    ok = False
    try:
        data = (
            await provider.edit(kw["image"], str(kw["instructions"]))  # type: ignore[arg-type]
            if op == "edit"
            else await provider.generate(str(kw["prompt"]))
        )
        ok = True
        return to_webp(data)
    except NotImplementedError as e:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "ספק התמונות אינו ממומש") from e
    except Exception as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "עיבוד התמונה נכשל") from e
    finally:
        db.add(
            AICall(
                user_id=user_id,
                feature=AIFeature.IMAGE,
                model=type(provider).__name__,
                latency_ms=int((time.perf_counter() - start) * 1000),
                status="ok" if ok else "error",
            )
        )
        db.commit()


async def _read_upload(file: UploadFile) -> bytes:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "יש להעלות JPG, PNG או WebP")
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "הקובץ גדול מ-10MB")
    try:
        return to_webp(data)
    except (UnidentifiedImageError, OSError) as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "הקובץ אינו תמונה תקינה") from e


@router.get("/recipes/{recipe_id}/images", response_model=list[ImageOut], summary="תמונות המתכון")
def list_images(recipe_id: int, db: DbSession, user: ContentManager) -> list[ImageOut]:
    _recipe(db, recipe_id)
    images = db.scalars(select(RecipeImage).where(RecipeImage.recipe_id == recipe_id))
    return [_out(i) for i in images]


@router.post(
    "/recipes/{recipe_id}/images",
    response_model=ImageOut,
    status_code=status.HTTP_201_CREATED,
    summary="העלאה, עיבוד או יצירה של תמונה",
    dependencies=[AIRateLimited],
)
async def add_image(
    recipe_id: int,
    db: DbSession,
    user: ContentManager,
    provider: Images,
    mode: Annotated[Literal["upload", "generate"], Form()],
    file: Annotated[UploadFile | None, File()] = None,
    enhance: Annotated[bool, Form()] = True,
    prompt: Annotated[str | None, Form(max_length=1000)] = None,
) -> ImageOut:
    """`upload`: home photo, optionally enhanced by the model.
    `generate`: new image from the manager's prompt, or from the recipe when empty.
    The result is not shown publicly until approved."""
    recipe = _recipe(db, recipe_id)
    image = RecipeImage(recipe_id=recipe.id, approved=False, is_primary=False)

    if mode == "upload":
        if file is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "חסר קובץ להעלאה")
        original = await _read_upload(file)
        image.original_path = save_image(recipe.id, original, "original")
        image.origin = ImageOrigin.UPLOAD
        if enhance:
            instructions = prompt or ENHANCE_INSTRUCTIONS
            processed = await _call_provider(
                db, provider, user.id, "edit", image=original, instructions=instructions
            )
            image.processed_path = save_image(recipe.id, processed, "processed")
            image.origin = ImageOrigin.AI_EDIT
            image.prompt = instructions
    else:
        text = prompt or default_prompt(recipe)
        generated = await _call_provider(db, provider, user.id, "generate", prompt=text)
        image.processed_path = save_image(recipe.id, generated, "generated")
        image.origin = ImageOrigin.AI_GENERATE
        image.prompt = text

    db.add(image)
    db.flush()
    log_action(db, user, "image.create", "recipe_image", image.id, {"origin": image.origin})
    db.commit()
    return _out(image)


def _image(db: Session, image_id: int) -> RecipeImage:
    image = db.get(RecipeImage, image_id)
    if image is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "התמונה לא נמצאה")
    return image


@router.post("/images/{image_id}/approve", response_model=ImageOut, summary="אישור תמונה כראשית")
def approve_image(
    image_id: int, body: ApproveImageIn, db: DbSession, user: ContentManager
) -> ImageOut:
    image = _image(db, image_id)
    if body.use_original and image.original_path is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "לתמונה זו אין מקור")
    for other in db.scalars(select(RecipeImage).where(RecipeImage.recipe_id == image.recipe_id)):
        other.is_primary = False
    image.approved = True
    image.is_primary = True
    image.use_original = body.use_original
    log_action(db, user, "image.approve", "recipe_image", image.id, body.model_dump())
    db.commit()
    return _out(image)


@router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT, summary="מחיקת תמונה")
def remove_image(image_id: int, db: DbSession, user: ContentManager) -> Response:
    image = _image(db, image_id)
    delete_image(image.original_path)
    delete_image(image.processed_path)
    log_action(db, user, "image.delete", "recipe_image", image.id)
    db.delete(image)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
