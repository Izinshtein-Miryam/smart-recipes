from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Recipe
from tests.conftest import login_as


def _id(db: Session, slug: str) -> int:
    recipe = db.scalar(select(Recipe).where(Recipe.slug == slug))
    assert recipe is not None
    return recipe.id


def test_favorites_require_login(client: TestClient) -> None:
    assert client.get("/api/favorites").status_code == 401


def test_favorites_flow(client: TestClient, seeded_db: Session) -> None:
    login_as(client, seeded_db)
    rid = _id(seeded_db, "salat-kinoa")
    assert client.post(f"/api/favorites/{rid}").status_code == 204
    assert client.post(f"/api/favorites/{rid}").status_code == 204  # idempotent
    assert [r["id"] for r in client.get("/api/favorites").json()] == [rid]
    assert client.delete(f"/api/favorites/{rid}").status_code == 204
    assert client.get("/api/favorites").json() == []
    assert client.post("/api/favorites/9999").status_code == 404


def test_shopping_list_merges_same_ingredient(client: TestClient, seeded_db: Session) -> None:
    login_as(client, seeded_db)
    shakshuka = _id(seeded_db, "shakshuka-yeruka")
    salad = _id(seeded_db, "salat-kinoa")

    client.post("/api/shopping-list", json={"recipe_id": shakshuka})
    items = client.post("/api/shopping-list", json={"recipe_id": salad, "servings": 8}).json()

    onion = [i for i in items if i["name"] == "בצל"]
    assert len(onion) == 1
    assert onion[0]["quantity"] == 1 + 0.5 * 2  # salad scaled from 4 to 8 servings
    assert sorted(onion[0]["source_recipe_ids"]) == sorted([shakshuka, salad])
    oil = next(i for i in items if i["name"] == "שמן זית")
    assert oil["quantity"] == 2 + 6


def test_shopping_list_item_operations(client: TestClient, seeded_db: Session) -> None:
    login_as(client, seeded_db)
    items = client.post(
        "/api/shopping-list", json={"recipe_id": _id(seeded_db, "salat-kinoa")}
    ).json()
    first = items[0]["id"]

    patched = client.patch(f"/api/shopping-list/{first}", json={"checked": True, "quantity": 3})
    assert patched.json()["checked"] is True
    assert patched.json()["quantity"] == 3

    assert client.delete(f"/api/shopping-list/{first}").status_code == 204
    assert len(client.get("/api/shopping-list").json()) == len(items) - 1
    assert client.delete("/api/shopping-list").status_code == 204
    assert client.get("/api/shopping-list").json() == []


def test_shopping_list_is_per_user(client: TestClient, seeded_db: Session) -> None:
    login_as(client, seeded_db, email="foo@example.com")
    items = client.post(
        "/api/shopping-list", json={"recipe_id": _id(seeded_db, "salat-kinoa")}
    ).json()
    login_as(client, seeded_db, email="bar@example.com")
    assert client.get("/api/shopping-list").json() == []
    assert client.patch(f"/api/shopping-list/{items[0]['id']}", json={}).status_code == 404
    assert client.delete(f"/api/shopping-list/{items[0]['id']}").status_code == 404
    assert client.post("/api/shopping-list", json={"recipe_id": 9999}).status_code == 404


def test_profile_update(client: TestClient, seeded_db: Session) -> None:
    login_as(client, seeded_db)
    res = client.patch("/api/me", json={"display_name": "bar", "dietary_prefs": ["gluten_free"]})
    assert res.json()["display_name"] == "bar"
    assert res.json()["dietary_prefs"] == ["gluten_free"]
