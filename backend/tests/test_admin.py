from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import RecipeStatus
from app.services import storage

from .conftest import FakeAi, make_recipe

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def test_login(client: TestClient) -> None:
    assert client.post("/api/admin/login", json={"password": "wrong"}).status_code == 401
    ok = client.post("/api/admin/login", json={"password": "lorem-ipsum"})
    assert ok.status_code == 200
    assert ok.json()["token_type"] == "bearer"


def test_admin_routes_require_token(client: TestClient) -> None:
    assert client.get("/api/admin/recipes").status_code == 401
    bad = {"Authorization": "Bearer not-a-token"}
    assert client.get("/api/admin/recipes", headers=bad).status_code == 401


def test_queue_lists_pending(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    make_recipe(db, title="approved")
    make_recipe(db, title="pending", status=RecipeStatus.PENDING)
    titles = [r["title"] for r in client.get("/api/admin/recipes", headers=admin_headers).json()]
    assert titles == ["pending"]


def test_update(client: TestClient, db: Session, admin_headers: dict[str, str]) -> None:
    recipe = make_recipe(db, status=RecipeStatus.PENDING)
    body = {
        "lang": "he", "title": "bar", "description": "Lorem", "servings": 3, "prep_minutes": 5,
        "difficulty": "hard", "equipment": ["no_cook"], "kashrut": "dairy",
        "ingredients": [{"name": "baz", "quantity": None, "unit": None, "note": None}],
        "steps": ["foo"],
    }  # fmt: skip
    res = client.put(f"/api/admin/recipes/{recipe.id}", json=body, headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["title"] == "bar"
    assert res.json()["kashrut"] == "dairy"


def test_approve_publishes_with_nutrition_and_image(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    rel = storage.save_pending(PNG)
    recipe = make_recipe(db, status=RecipeStatus.PENDING, image_path=rel)
    res = client.post(f"/api/admin/recipes/{recipe.id}/approve", headers=admin_headers)
    body = res.json()
    assert res.status_code == 200
    assert body["status"] == "approved"
    assert body["nutrition"]["calories"] == 100
    assert body["nutrition"]["confidence"] == "medium"
    assert body["image_url"] and client.get(body["image_url"]).content == PNG
    assert client.get(f"/api/recipes/{recipe.id}").status_code == 200


def test_approve_survives_ai_failure_and_can_be_retried(
    client: TestClient, db: Session, admin_headers: dict[str, str], fake_ai: FakeAi
) -> None:
    recipe = make_recipe(db, status=RecipeStatus.PENDING)
    fake_ai.fail = True
    first = client.post(f"/api/admin/recipes/{recipe.id}/approve", headers=admin_headers).json()
    assert first["status"] == "approved"
    assert first["nutrition"] is None
    fake_ai.fail = False
    second = client.post(f"/api/admin/recipes/{recipe.id}/approve", headers=admin_headers).json()
    assert second["nutrition"]["calories"] == 100
    assert second["approved_at"] == first["approved_at"]


def test_reject_then_approve_conflicts(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    recipe = make_recipe(db, status=RecipeStatus.PENDING)
    assert (
        client.post(f"/api/admin/recipes/{recipe.id}/reject", headers=admin_headers).status_code
        == 200
    )
    assert (
        client.post(f"/api/admin/recipes/{recipe.id}/approve", headers=admin_headers).status_code
        == 409
    )
    db.refresh(recipe)
    assert recipe.status == RecipeStatus.REJECTED


def test_unknown_recipe_is_404(client: TestClient, admin_headers: dict[str, str]) -> None:
    res = client.post(
        "/api/admin/recipes/00000000-0000-0000-0000-000000000000/approve", headers=admin_headers
    )
    assert res.status_code == 404
