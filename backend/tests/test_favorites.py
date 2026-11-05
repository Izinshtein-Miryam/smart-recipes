from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Recipe, RecipeStatus
from tests.conftest import login, make_user


def _recipe_id(db: Session, slug: str) -> int:
    return db.query(Recipe).filter_by(slug=slug).one().id


def _login_new(client: TestClient, db: Session, email: str = "foo@example.com") -> None:
    make_user(db, email)
    login(client, email)


def test_auth_required(client: TestClient) -> None:
    assert client.get("/api/favorites").status_code == 401
    assert client.post("/api/favorites/1").status_code == 401
    assert client.delete("/api/favorites/1").status_code == 401


def test_add_list_remove(client: TestClient, seeded_db: Session) -> None:
    _login_new(client, seeded_db)
    rid = _recipe_id(seeded_db, "salat-kinoa")
    assert client.get("/api/favorites").json() == {"items": []}

    assert client.post(f"/api/favorites/{rid}").status_code == 204
    items = client.get("/api/favorites").json()["items"]
    assert [i["slug"] for i in items] == ["salat-kinoa"]

    assert client.delete(f"/api/favorites/{rid}").status_code == 204
    assert client.get("/api/favorites").json()["items"] == []


def test_add_is_idempotent(client: TestClient, seeded_db: Session) -> None:
    _login_new(client, seeded_db)
    rid = _recipe_id(seeded_db, "salat-kinoa")
    assert client.post(f"/api/favorites/{rid}").status_code == 204
    assert client.post(f"/api/favorites/{rid}").status_code == 204
    assert len(client.get("/api/favorites").json()["items"]) == 1


def test_remove_missing_is_noop(client: TestClient, seeded_db: Session) -> None:
    _login_new(client, seeded_db)
    assert client.delete("/api/favorites/999999").status_code == 204


def test_add_unknown_recipe(client: TestClient, seeded_db: Session) -> None:
    _login_new(client, seeded_db)
    assert client.post("/api/favorites/999999").status_code == 404


def test_add_unpublished_recipe(client: TestClient, seeded_db: Session) -> None:
    _login_new(client, seeded_db)
    recipe = seeded_db.query(Recipe).filter_by(slug="salat-kinoa").one()
    recipe.status = RecipeStatus.HIDDEN
    seeded_db.commit()
    assert client.post(f"/api/favorites/{recipe.id}").status_code == 404


def test_hidden_recipe_not_listed(client: TestClient, seeded_db: Session) -> None:
    _login_new(client, seeded_db)
    recipe = seeded_db.query(Recipe).filter_by(slug="salat-kinoa").one()
    client.post(f"/api/favorites/{recipe.id}")
    recipe.status = RecipeStatus.HIDDEN
    seeded_db.commit()
    assert client.get("/api/favorites").json()["items"] == []


def test_favorites_isolated_between_users(client: TestClient, seeded_db: Session) -> None:
    rid = _recipe_id(seeded_db, "salat-kinoa")
    _login_new(client, seeded_db, "foo@example.com")
    client.post(f"/api/favorites/{rid}")

    make_user(seeded_db, "bar@example.com")
    login(client, "bar@example.com")
    assert client.get("/api/favorites").json()["items"] == []
    client.delete(f"/api/favorites/{rid}")  # must not affect the other user

    login(client, "foo@example.com")
    assert len(client.get("/api/favorites").json()["items"]) == 1
