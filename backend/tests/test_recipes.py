from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Recipe, RecipeStatus
from app.seed import seed


def test_list_recipes(client: TestClient) -> None:
    res = client.get("/api/recipes")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 3
    assert {r["slug"] for r in body["items"]} >= {"shakshuka-yeruka", "salat-kinoa"}


def test_list_filters(client: TestClient) -> None:
    assert client.get("/api/recipes", params={"kosher_type": "dairy"}).json()["total"] == 1
    assert client.get("/api/recipes", params={"kosher_type": "meat"}).json()["total"] == 1
    assert client.get("/api/recipes", params={"dish_type": "main"}).json()["total"] == 2
    assert client.get("/api/recipes", params={"max_minutes": 25}).json()["total"] == 1
    assert client.get("/api/recipes", params={"difficulty": "medium"}).json()["total"] == 1
    assert client.get("/api/recipes", params={"q": "קינואה"}).json()["total"] == 1


def test_pagination(client: TestClient) -> None:
    body = client.get("/api/recipes", params={"page_size": 2, "page": 2}).json()
    assert len(body["items"]) == 1
    assert body["page"] == 2


def test_hidden_recipes_not_listed(client: TestClient, seeded_db: Session) -> None:
    recipe = seeded_db.query(Recipe).filter_by(slug="salat-kinoa").one()
    recipe.status = RecipeStatus.HIDDEN
    seeded_db.commit()
    assert client.get("/api/recipes").json()["total"] == 2
    assert client.get("/api/recipes/salat-kinoa").status_code == 404


def test_get_recipe_scaled(client: TestClient) -> None:
    base = client.get("/api/recipes/shakshuka-yeruka").json()
    assert base["servings"] == 2
    assert base["kosher_type"] == "dairy"
    assert base["steps"][0]["order"] == 1
    eggs = next(i for i in base["ingredients"] if i["name"] == "ביצים")
    assert eggs["quantity"] == 4

    scaled = client.get("/api/recipes/shakshuka-yeruka", params={"servings": 4}).json()
    eggs = next(i for i in scaled["ingredients"] if i["name"] == "ביצים")
    assert eggs["quantity"] == 8


def test_get_missing_recipe(client: TestClient) -> None:
    assert client.get("/api/recipes/lorem-ipsum").status_code == 404


def test_seed_is_idempotent(seeded_db: Session) -> None:
    assert seed(seeded_db) == 0
