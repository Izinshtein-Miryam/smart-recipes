from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import RecipeStatus

from .conftest import FakeAi, make_recipe


def test_fridge_search(client: TestClient, db: Session) -> None:
    make_recipe(db)
    res = client.post("/api/ai/fridge-search", json={"ingredients": ["bar"], "lang": "he"})
    assert res.status_code == 200
    item = res.json()["results"][0]
    assert item["match_score"] == 80
    assert item["missing_ingredients"] == ["baz"]
    assert item["recipe"]["title"] == "foo"


def test_fridge_search_without_candidates_skips_ai(client: TestClient, fake_ai: FakeAi) -> None:
    fake_ai.fail = True  # would return 503 if the AI were called
    res = client.post("/api/ai/fridge-search", json={"ingredients": ["bar"], "lang": "en"})
    assert res.json() == {"results": []}


def test_fridge_search_validates_input(client: TestClient) -> None:
    assert (
        client.post("/api/ai/fridge-search", json={"ingredients": [], "lang": "he"}).status_code
        == 422
    )


def test_adapt(client: TestClient, db: Session) -> None:
    recipe = make_recipe(db)
    res = client.post("/api/ai/adapt", json={"recipe_id": str(recipe.id), "instruction": "foo"})
    assert res.status_code == 200
    assert res.json()["feasible"] is True


def test_adapt_requires_approved_recipe(client: TestClient, db: Session) -> None:
    recipe = make_recipe(db, status=RecipeStatus.PENDING)
    res = client.post("/api/ai/adapt", json={"recipe_id": str(recipe.id), "instruction": "foo"})
    assert res.status_code == 404


def test_ai_failure_maps_to_503(client: TestClient, db: Session, fake_ai: FakeAi) -> None:
    recipe = make_recipe(db)
    fake_ai.fail = True
    res = client.post("/api/ai/adapt", json={"recipe_id": str(recipe.id), "instruction": "foo"})
    assert res.status_code == 503
    assert res.json() == {"detail": "ai_unavailable"}


def test_chat_is_not_implemented_yet(client: TestClient, db: Session) -> None:
    recipe = make_recipe(db)
    res = client.post("/api/ai/chat", json={"recipe_id": str(recipe.id), "message": "foo"})
    assert res.status_code == 501
