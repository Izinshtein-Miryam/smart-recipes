from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Recipe, RecipeStatus, ShoppingListItem
from tests.conftest import login, make_user


def _recipe_id(db: Session, slug: str) -> int:
    return db.query(Recipe).filter_by(slug=slug).one().id


def _login_new(client: TestClient, db: Session, email: str = "foo@example.com") -> None:
    make_user(db, email)
    login(client, email)


def _items(client: TestClient) -> dict[str, Any]:
    res = client.get("/api/shopping-list")
    assert res.status_code == 200
    return {i["name"]: i for i in res.json()["items"]}


def test_auth_required(client: TestClient) -> None:
    assert client.get("/api/shopping-list").status_code == 401
    assert client.post("/api/shopping-list", json={"recipe_id": 1}).status_code == 401
    assert client.patch("/api/shopping-list/1", json={"checked": True}).status_code == 401
    assert client.delete("/api/shopping-list/1").status_code == 401
    assert client.delete("/api/shopping-list").status_code == 401


def test_empty_list(client: TestClient, seeded_db: Session) -> None:
    _login_new(client, seeded_db)
    assert client.get("/api/shopping-list").json() == {"items": []}


def test_add_recipe(client: TestClient, seeded_db: Session) -> None:
    _login_new(client, seeded_db)
    rid = _recipe_id(seeded_db, "shakshuka-yeruka")
    res = client.post("/api/shopping-list", json={"recipe_id": rid})
    assert res.status_code == 200
    items = {i["name"]: i for i in res.json()["items"]}
    assert len(items) == 6
    assert items["ביצים"]["quantity"] == 4
    assert items["ביצים"]["unit"] == "יחידות"
    assert items["ביצים"]["source_recipe_ids"] == [rid]
    assert items["ביצים"]["checked"] is False


def test_add_recipe_scaled(client: TestClient, seeded_db: Session) -> None:
    _login_new(client, seeded_db)
    rid = _recipe_id(seeded_db, "shakshuka-yeruka")
    client.post("/api/shopping-list", json={"recipe_id": rid, "servings": 4})
    assert _items(client)["ביצים"]["quantity"] == 8


def test_merge_same_ingredient_across_recipes(client: TestClient, seeded_db: Session) -> None:
    _login_new(client, seeded_db)
    r1 = _recipe_id(seeded_db, "shakshuka-yeruka")
    r2 = _recipe_id(seeded_db, "salat-kinoa")
    client.post("/api/shopping-list", json={"recipe_id": r1})
    client.post("/api/shopping-list", json={"recipe_id": r2})
    items = _items(client)
    assert items["שמן זית"]["quantity"] == 5  # 2 + 3, same unit
    assert items["שמן זית"]["source_recipe_ids"] == [r1, r2]
    assert items["בצל"]["quantity"] == 1.5
    assert items["קינואה"]["source_recipe_ids"] == [r2]
    assert items["מלח"]["quantity"] == 1.5
    assert len(items) == 8  # 6 + 5 lines, minus 3 merged (olive oil, onion, salt)


def test_same_ingredient_different_unit_not_merged(client: TestClient, seeded_db: Session) -> None:
    _login_new(client, seeded_db)
    rid = _recipe_id(seeded_db, "shakshuka-yeruka")
    client.post("/api/shopping-list", json={"recipe_id": rid})
    row = seeded_db.get(ShoppingListItem, _items(client)["מלח"]["id"])
    assert row is not None
    row.unit = "קורט"  # the next add cannot merge into a different unit
    seeded_db.commit()

    client.post("/api/shopping-list", json={"recipe_id": rid})
    salts = [i for i in client.get("/api/shopping-list").json()["items"] if i["name"] == "מלח"]
    assert sorted(i["unit"] for i in salts) == ["כפית", "קורט"]


def test_readd_same_recipe_accumulates_with_single_source(
    client: TestClient, seeded_db: Session
) -> None:
    _login_new(client, seeded_db)
    rid = _recipe_id(seeded_db, "shakshuka-yeruka")
    client.post("/api/shopping-list", json={"recipe_id": rid})
    client.post("/api/shopping-list", json={"recipe_id": rid})
    item = _items(client)["ביצים"]
    assert item["quantity"] == 8
    assert item["source_recipe_ids"] == [rid]


def test_readd_unchecks_item(client: TestClient, seeded_db: Session) -> None:
    _login_new(client, seeded_db)
    rid = _recipe_id(seeded_db, "shakshuka-yeruka")
    client.post("/api/shopping-list", json={"recipe_id": rid})
    item_id = _items(client)["ביצים"]["id"]
    client.patch(f"/api/shopping-list/{item_id}", json={"checked": True})
    assert _items(client)["ביצים"]["checked"] is True
    client.post("/api/shopping-list", json={"recipe_id": rid})
    assert _items(client)["ביצים"]["checked"] is False


def test_add_unknown_or_hidden_recipe(client: TestClient, seeded_db: Session) -> None:
    _login_new(client, seeded_db)
    assert client.post("/api/shopping-list", json={"recipe_id": 999999}).status_code == 404
    recipe = seeded_db.query(Recipe).filter_by(slug="salat-kinoa").one()
    recipe.status = RecipeStatus.HIDDEN
    seeded_db.commit()
    assert client.post("/api/shopping-list", json={"recipe_id": recipe.id}).status_code == 404


def test_add_validation(client: TestClient, seeded_db: Session) -> None:
    _login_new(client, seeded_db)
    rid = _recipe_id(seeded_db, "salat-kinoa")
    assert client.post("/api/shopping-list", json={}).status_code == 422
    body = {"recipe_id": rid, "servings": 0}
    assert client.post("/api/shopping-list", json=body).status_code == 422


def test_check_and_uncheck(client: TestClient, seeded_db: Session) -> None:
    _login_new(client, seeded_db)
    client.post("/api/shopping-list", json={"recipe_id": _recipe_id(seeded_db, "salat-kinoa")})
    item_id = _items(client)["קינואה"]["id"]
    res = client.patch(f"/api/shopping-list/{item_id}", json={"checked": True})
    assert res.status_code == 200
    assert _items(client)["קינואה"]["checked"] is True
    client.patch(f"/api/shopping-list/{item_id}", json={"checked": False})
    assert _items(client)["קינואה"]["checked"] is False


def test_patch_missing_item_and_bad_body(client: TestClient, seeded_db: Session) -> None:
    _login_new(client, seeded_db)
    assert client.patch("/api/shopping-list/999", json={"checked": True}).status_code == 404
    assert client.patch("/api/shopping-list/999", json={}).status_code == 422


def test_delete_item(client: TestClient, seeded_db: Session) -> None:
    _login_new(client, seeded_db)
    client.post("/api/shopping-list", json={"recipe_id": _recipe_id(seeded_db, "salat-kinoa")})
    item_id = _items(client)["קינואה"]["id"]
    assert client.delete(f"/api/shopping-list/{item_id}").status_code == 204
    assert "קינואה" not in _items(client)
    assert client.delete(f"/api/shopping-list/{item_id}").status_code == 404


def test_clear_list(client: TestClient, seeded_db: Session) -> None:
    _login_new(client, seeded_db)
    client.post("/api/shopping-list", json={"recipe_id": _recipe_id(seeded_db, "salat-kinoa")})
    assert client.delete("/api/shopping-list").status_code == 204
    assert client.get("/api/shopping-list").json() == {"items": []}
    assert client.delete("/api/shopping-list").status_code == 204


def test_isolation_between_users(client: TestClient, seeded_db: Session) -> None:
    rid = _recipe_id(seeded_db, "salat-kinoa")
    _login_new(client, seeded_db, "foo@example.com")
    client.post("/api/shopping-list", json={"recipe_id": rid})
    foo_item_id = _items(client)["קינואה"]["id"]

    make_user(seeded_db, "bar@example.com")
    login(client, "bar@example.com")
    assert client.get("/api/shopping-list").json() == {"items": []}
    patch = client.patch(f"/api/shopping-list/{foo_item_id}", json={"checked": True})
    assert patch.status_code == 404
    assert client.delete(f"/api/shopping-list/{foo_item_id}").status_code == 404
    client.post("/api/shopping-list", json={"recipe_id": rid})
    assert _items(client)["קינואה"]["id"] != foo_item_id
    client.delete("/api/shopping-list")

    login(client, "foo@example.com")
    item = _items(client)["קינואה"]
    assert item["id"] == foo_item_id
    assert item["checked"] is False
