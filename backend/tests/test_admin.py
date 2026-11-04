import io
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AICall, AuditLog, Ingredient, Recipe, Role
from tests.conftest import login_as


def ing(db: Session, name: str) -> int:
    row = db.scalar(select(Ingredient).where(Ingredient.name == name))
    assert row is not None
    return row.id


def recipe_body(db: Session, **overrides: Any) -> dict[str, Any]:
    eggs, tomato = ing(db, "ביצים"), ing(db, "עגבניות")
    body: dict[str, Any] = {
        "title": "שקשוקה אדומה",
        "slug": "shakshuka-aduma",
        "description": "lorem ipsum",
        "dish_type": "main",
        "difficulty": "easy",
        "prep_minutes": 10,
        "cook_minutes": 20,
        "servings": 4,
        "time_tags": ["morning"],
        "diet_tags": [],
        "status": "draft",
        "ingredients": [
            {"ingredient_id": eggs, "quantity": 6, "unit": "יחידות"},
            {"ingredient_id": tomato, "quantity": 4, "unit": "יחידות"},
        ],
        "steps": [
            {"text": "foo", "ingredient_ids": [tomato]},
            {"text": "bar", "timer_seconds": 600, "ingredient_ids": [eggs]},
        ],
    }
    body.update(overrides)
    return body


def test_create_update_publish_delete(client: TestClient, seeded_db: Session) -> None:
    login_as(client, seeded_db, Role.CONTENT_MANAGER)
    res = client.post("/api/admin/recipes", json=recipe_body(seeded_db))
    assert res.status_code == 201, res.text
    created = res.json()
    assert created["kosher_type"] == "parve"
    rid = created["id"]

    # Draft is not public.
    assert client.get("/api/recipes", params={"q": "שקשוקה אדומה"}).json()["total"] == 0

    body = recipe_body(seeded_db, title="שקשוקה אדומה חריפה")
    assert client.put(f"/api/admin/recipes/{rid}", json=body).json()["title"] == body["title"]

    res = client.patch(f"/api/admin/recipes/{rid}/status", json={"status": "published"})
    assert res.json()["status"] == "published"
    client.post("/api/auth/logout")
    assert client.get("/api/recipes/shakshuka-aduma").status_code == 200

    login_as(client, seeded_db, Role.SYSADMIN)
    assert client.get(f"/api/admin/recipes/{rid}").json()["steps"][1]["timer_seconds"] == 600
    assert client.delete(f"/api/admin/recipes/{rid}").status_code == 204
    assert client.get(f"/api/admin/recipes/{rid}").status_code == 404

    actions = [a.action for a in seeded_db.scalars(select(AuditLog).order_by(AuditLog.id))]
    assert actions == ["recipe.create", "recipe.update", "recipe.status", "recipe.delete"]


def test_create_generates_slug_and_embedding(client: TestClient, seeded_db: Session) -> None:
    login_as(client, seeded_db, Role.CONTENT_MANAGER)
    res = client.post("/api/admin/recipes", json=recipe_body(seeded_db, slug=None))
    slug = res.json()["slug"]
    assert slug.startswith("recipe-")
    recipe = seeded_db.scalar(select(Recipe).where(Recipe.slug == slug))
    assert recipe is not None and recipe.embedding is not None


def test_create_rejects_meat_dairy_mix(client: TestClient, seeded_db: Session) -> None:
    login_as(client, seeded_db, Role.CONTENT_MANAGER)
    body = recipe_body(
        seeded_db,
        ingredients=[
            {"ingredient_id": ing(seeded_db, "חזה עוף"), "quantity": 1, "unit": "גרם"},
            {"ingredient_id": ing(seeded_db, "גבינה בולגרית"), "quantity": 1, "unit": "גרם"},
        ],
        steps=[{"text": "foo"}],
    )
    res = client.post("/api/admin/recipes", json=body)
    assert res.status_code == 422
    assert "בשריים" in res.json()["detail"]


def test_create_validation_errors(client: TestClient, seeded_db: Session) -> None:
    login_as(client, seeded_db, Role.CONTENT_MANAGER)
    missing = recipe_body(seeded_db, ingredients=[{"ingredient_id": 9999}], steps=[{"text": "x"}])
    assert client.post("/api/admin/recipes", json=missing).status_code == 422
    bad_step = recipe_body(seeded_db, steps=[{"text": "x", "ingredient_ids": [9999]}])
    assert client.post("/api/admin/recipes", json=bad_step).status_code == 422
    clash = recipe_body(seeded_db, slug="salat-kinoa")
    assert client.post("/api/admin/recipes", json=clash).status_code == 409
    bad_slug = recipe_body(seeded_db, slug="Not A Slug")
    assert client.post("/api/admin/recipes", json=bad_slug).status_code == 422


def test_admin_list_filters(client: TestClient, seeded_db: Session) -> None:
    login_as(client, seeded_db, Role.CONTENT_MANAGER)
    client.post("/api/admin/recipes", json=recipe_body(seeded_db))
    assert len(client.get("/api/admin/recipes").json()) == 4
    assert len(client.get("/api/admin/recipes", params={"status": "draft"}).json()) == 1
    assert len(client.get("/api/admin/recipes", params={"q": "kinoa"}).json()) == 1
    assert client.get("/api/admin/recipes", params={"source": "ai"}).json() == []


def test_admin_drafts_visible_to_content_manager(client: TestClient, seeded_db: Session) -> None:
    login_as(client, seeded_db, Role.CONTENT_MANAGER)
    client.post("/api/admin/recipes", json=recipe_body(seeded_db))
    assert client.get("/api/recipes/shakshuka-aduma").json()["status"] == "draft"


def test_ingredients_search_and_create(client: TestClient, seeded_db: Session) -> None:
    assert [i["name"] for i in client.get("/api/ingredients", params={"q": "גבינה"}).json()] == [
        "גבינה בולגרית"
    ]
    body = {"name": "חלב", "category": "מוצרי חלב", "kosher_type": "dairy"}
    assert client.post("/api/admin/ingredients", json=body).status_code == 401
    login_as(client, seeded_db, Role.CONTENT_MANAGER)
    assert client.post("/api/admin/ingredients", json=body).status_code == 201
    assert client.post("/api/admin/ingredients", json=body).status_code == 409


# ---- Images ------------------------------------------------------------------


def png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (20, 20), (200, 100, 50)).save(buf, format="PNG")
    return buf.getvalue()


def _salad_id(db: Session) -> int:
    recipe = db.scalar(select(Recipe).where(Recipe.slug == "salat-kinoa"))
    assert recipe is not None
    return recipe.id


def test_upload_enhance_and_approve(
    client: TestClient, seeded_db: Session, media_dir: Path
) -> None:
    login_as(client, seeded_db, Role.CONTENT_MANAGER)
    rid = _salad_id(seeded_db)
    res = client.post(
        f"/api/admin/recipes/{rid}/images",
        data={"mode": "upload", "enhance": "true"},
        files={"file": ("foo.png", png_bytes(), "image/png")},
    )
    assert res.status_code == 201, res.text
    image = res.json()
    assert image["origin"] == "ai_edit"
    assert image["approved"] is False
    assert image["original_url"] and image["processed_url"]
    assert (media_dir / image["processed_url"].removeprefix("/media/")).exists()

    # Not public until approved.
    assert client.get("/api/recipes/salat-kinoa").json()["image_url"] is None
    approved = client.post(f"/api/admin/images/{image['id']}/approve", json={}).json()
    assert approved["is_primary"] is True
    assert client.get("/api/recipes/salat-kinoa").json()["image_url"] == image["processed_url"]

    # Revert to the original photo.
    client.post(f"/api/admin/images/{image['id']}/approve", json={"use_original": True})
    assert client.get("/api/recipes/salat-kinoa").json()["image_url"] == image["original_url"]
    assert seeded_db.scalars(select(AICall)).one().feature == "image"


def test_upload_without_enhance(client: TestClient, seeded_db: Session) -> None:
    login_as(client, seeded_db, Role.CONTENT_MANAGER)
    res = client.post(
        f"/api/admin/recipes/{_salad_id(seeded_db)}/images",
        data={"mode": "upload", "enhance": "false"},
        files={"file": ("foo.png", png_bytes(), "image/png")},
    )
    assert res.json()["origin"] == "upload"
    assert res.json()["processed_url"] is None


def test_generate_image_uses_recipe_prompt(client: TestClient, seeded_db: Session) -> None:
    login_as(client, seeded_db, Role.CONTENT_MANAGER)
    rid = _salad_id(seeded_db)
    image = client.post(f"/api/admin/recipes/{rid}/images", data={"mode": "generate"}).json()
    assert image["origin"] == "ai_generate"
    assert "סלט קינואה" in image["prompt"]
    assert len(client.get(f"/api/admin/recipes/{rid}/images").json()) == 1

    with_original = client.post(
        f"/api/admin/images/{image['id']}/approve", json={"use_original": True}
    )
    assert with_original.status_code == 422
    assert client.delete(f"/api/admin/images/{image['id']}").status_code == 204
    assert client.get(f"/api/admin/recipes/{rid}/images").json() == []


def test_upload_validation(client: TestClient, seeded_db: Session) -> None:
    login_as(client, seeded_db, Role.CONTENT_MANAGER)
    url = f"/api/admin/recipes/{_salad_id(seeded_db)}/images"
    assert client.post(url, data={"mode": "upload"}).status_code == 422
    text = client.post(
        url, data={"mode": "upload"}, files={"file": ("a.txt", b"foo", "text/plain")}
    )
    assert text.status_code == 415
    broken = client.post(
        url, data={"mode": "upload"}, files={"file": ("a.png", b"not an image", "image/png")}
    )
    assert broken.status_code == 422
    huge = client.post(
        url,
        data={"mode": "upload"},
        files={"file": ("a.png", b"0" * (10 * 1024 * 1024 + 1), "image/png")},
    )
    assert huge.status_code == 413
    assert (
        client.post("/api/admin/recipes/9999/images", data={"mode": "generate"}).status_code == 404
    )
    assert client.post("/api/admin/images/9999/approve", json={}).status_code == 404
