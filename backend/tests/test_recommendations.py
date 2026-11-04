from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Recipe, RecipeIngredient
from app.services.embeddings.provider import to_blob
from app.services.recommendations import content_similarity
from tests.conftest import login_as


def test_home_morning_prefers_morning_recipes(client: TestClient) -> None:
    body = client.get("/api/recommendations/home", params={"at": "2026-11-01T08:00:00"}).json()
    assert body["context"] == "morning"
    assert body["title"] == "מתאים לארוחת בוקר"
    assert body["featured"]["slug"] == "shakshuka-yeruka"
    assert len(body["items"]) == 2


def test_home_contexts(client: TestClient) -> None:
    def ctx(at: str) -> str:
        return str(client.get("/api/recommendations/home", params={"at": at}).json()["context"])

    assert ctx("2026-11-01T13:00:00") == "noon"
    assert ctx("2026-11-01T20:00:00") == "evening"
    assert ctx("2026-11-05T20:00:00") == "make_ahead"  # Thursday


def test_home_evening_featured_is_tagged_main(client: TestClient) -> None:
    body = client.get("/api/recommendations/home", params={"at": "2026-11-01T20:00:00"}).json()
    assert body["featured"]["slug"] == "chaze-of-batanur"


def test_home_respects_dietary_prefs(client: TestClient, seeded_db: Session) -> None:
    login_as(client, seeded_db)
    client.patch("/api/me", json={"dietary_prefs": ["sugar_free"]})
    body = client.get("/api/recommendations/home").json()
    assert body["featured"]["slug"] == "salat-kinoa"
    assert body["items"] == []


def _id(db: Session, slug: str) -> int:
    recipe = db.scalar(select(Recipe).where(Recipe.slug == slug))
    assert recipe is not None
    return recipe.id


def test_similar_keeps_kosher_type_by_default(client: TestClient, seeded_db: Session) -> None:
    rid = _id(seeded_db, "salat-kinoa")
    assert client.get(f"/api/recipes/{rid}/similar").json() == []  # no other parve recipe
    any_type = client.get(f"/api/recipes/{rid}/similar", params={"any_type": True}).json()
    assert {r["slug"] for r in any_type} == {"shakshuka-yeruka", "chaze-of-batanur"}


def _recipe(ingredient_ids: list[int], embedding: list[float], tags: list[str]) -> Recipe:
    recipe = Recipe(dish_type="main", diet_tags=tags, time_tags=[], embedding=to_blob(embedding))
    recipe.ingredients = [RecipeIngredient(ingredient_id=i) for i in ingredient_ids]
    return recipe


def test_content_similarity_combines_embedding_ingredients_and_tags() -> None:
    base = _recipe([1, 2, 3], [1.0, 0.0], ["gluten_free"])
    twin = _recipe([1, 2, 3], [1.0, 0.0], ["gluten_free"])
    near = _recipe([1, 2, 9], [1.0, 0.0], [])
    far = _recipe([7, 8, 9], [0.0, 1.0], [])
    assert content_similarity(base, twin) == 1.0
    assert content_similarity(base, twin) > content_similarity(base, near)
    assert content_similarity(base, near) > content_similarity(base, far)
    assert content_similarity(base, _recipe([1], [-1.0, 0.0], [])) >= 0  # cosine clipped


def test_similar_unknown_recipe(client: TestClient) -> None:
    assert client.get("/api/recipes/9999/similar").status_code == 404
