from fastapi.testclient import TestClient
from sqlalchemy import ColumnElement
from sqlalchemy.orm import Session

from app.models import Difficulty, DishType, KosherType, Recipe, RecipeStatus
from app.seed import seed


def _count(db: Session, *criteria: ColumnElement[bool]) -> int:
    return db.query(Recipe).filter(*criteria).count()


def test_list_recipes(client: TestClient, seeded_db: Session) -> None:
    res = client.get("/api/recipes", params={"page_size": 100})
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == _count(seeded_db) >= 50
    assert {r["slug"] for r in body["items"]} >= {"shakshuka-yeruka", "salat-kinoa"}


def test_list_filters(client: TestClient, seeded_db: Session) -> None:
    def total(**params: str | int) -> int:
        return int(client.get("/api/recipes", params=params).json()["total"])

    assert total(kosher_type="dairy") == _count(seeded_db, Recipe.kosher_type == KosherType.DAIRY)
    assert total(kosher_type="meat") == _count(seeded_db, Recipe.kosher_type == KosherType.MEAT)
    assert total(dish_type="main") == _count(seeded_db, Recipe.dish_type == DishType.MAIN)
    fast = Recipe.prep_minutes + Recipe.cook_minutes <= 25
    assert total(max_minutes=25) == _count(seeded_db, fast)
    assert total(difficulty="medium") == _count(seeded_db, Recipe.difficulty == Difficulty.MEDIUM)
    assert total(q="קינואה") == 1


def test_pagination(client: TestClient, seeded_db: Session) -> None:
    body = client.get("/api/recipes", params={"page_size": 2, "page": 2}).json()
    assert len(body["items"]) == 2
    assert body["page"] == 2


def test_hidden_recipes_not_listed(client: TestClient, seeded_db: Session) -> None:
    before = client.get("/api/recipes").json()["total"]
    recipe = seeded_db.query(Recipe).filter_by(slug="salat-kinoa").one()
    recipe.status = RecipeStatus.HIDDEN
    seeded_db.commit()
    assert client.get("/api/recipes").json()["total"] == before - 1
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
