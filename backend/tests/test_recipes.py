from fastapi.testclient import TestClient
from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session

from app.models import Difficulty, DishType, KosherType, Recipe, RecipeStatus
from app.seed import seed


def _count(db: Session, *conditions: ColumnElement[bool]) -> int:
    return db.scalar(select(func.count()).select_from(Recipe).where(*conditions)) or 0


def test_list_recipes(client: TestClient) -> None:
    res = client.get("/api/recipes", params={"page_size": 100})
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 50
    assert len(body["items"]) == 50
    assert {r["slug"] for r in body["items"]} >= {"shakshuka-yeruka", "salat-kinoa"}


def test_list_filters(client: TestClient, seeded_db: Session) -> None:
    def total(**params: str | int) -> int:
        return int(client.get("/api/recipes", params=params).json()["total"])

    dairy = _count(seeded_db, Recipe.kosher_type == KosherType.DAIRY)
    assert dairy >= 15
    assert total(kosher_type="dairy") == dairy
    assert total(kosher_type="meat") == _count(seeded_db, Recipe.kosher_type == KosherType.MEAT)
    assert total(dish_type="main") == _count(seeded_db, Recipe.dish_type == DishType.MAIN)
    assert total(difficulty="medium") == _count(seeded_db, Recipe.difficulty == Difficulty.MEDIUM)
    quick = _count(seeded_db, Recipe.prep_minutes + Recipe.cook_minutes <= 25)
    assert 0 < quick < 50
    assert total(max_minutes=25) == quick
    assert total(q="קינואה") == 1
    assert total(kosher_type="dairy", dish_type="main") == _count(
        seeded_db, Recipe.kosher_type == KosherType.DAIRY, Recipe.dish_type == DishType.MAIN
    )


def test_pagination(client: TestClient) -> None:
    page1 = client.get("/api/recipes", params={"page_size": 20, "page": 1}).json()
    page3 = client.get("/api/recipes", params={"page_size": 20, "page": 3}).json()
    assert len(page1["items"]) == 20
    assert len(page3["items"]) == 10
    assert page3["page"] == 3
    assert page3["total"] == 50
    assert {r["slug"] for r in page1["items"]}.isdisjoint(r["slug"] for r in page3["items"])


def test_hidden_recipes_not_listed(client: TestClient, seeded_db: Session) -> None:
    recipe = seeded_db.query(Recipe).filter_by(slug="salat-kinoa").one()
    recipe.status = RecipeStatus.HIDDEN
    seeded_db.commit()
    assert client.get("/api/recipes").json()["total"] == 49
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
