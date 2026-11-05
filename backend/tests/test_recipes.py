import json
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Recipe, RecipeStatus

from .conftest import make_recipe

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def form(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "lang": "en",
        "title": "foo",
        "description": "Lorem ipsum",
        "servings": 2,
        "prep_minutes": 10,
        "difficulty": "easy",
        "kashrut": "parve",
        "equipment": ["oven", "stovetop"],
        "ingredients": json.dumps([{"name": "bar", "quantity": 1, "unit": None, "note": None}]),
        "steps": json.dumps(["baz"]),
    }
    return {**data, **overrides}


def test_list_returns_only_approved(client: TestClient, db: Session) -> None:
    make_recipe(db, title="approved")
    make_recipe(db, title="pending", status=RecipeStatus.PENDING)
    titles = [r["title"] for r in client.get("/api/recipes").json()]
    assert titles == ["approved"]


def test_list_filters(client: TestClient, db: Session) -> None:
    make_recipe(db, title="a", kashrut="meat", prep_minutes=20, equipment=["oven", "stovetop"])
    make_recipe(db, title="b", kashrut="dairy", prep_minutes=90, equipment=["no_cook"], lang="en")

    def titles(**params: Any) -> list[str]:
        return [r["title"] for r in client.get("/api/recipes", params=params).json()]

    assert titles(kashrut="meat") == ["a"]
    assert titles(max_minutes=30) == ["a"]
    assert titles(lang="en") == ["b"]
    assert titles(equipment=["oven", "stovetop"]) == ["a"]
    assert titles(equipment="no_cook") == ["b"]
    assert titles(q="b") == ["b"]
    assert titles(difficulty="hard") == []


def test_get_recipe(client: TestClient, db: Session) -> None:
    ok = make_recipe(db)
    hidden = make_recipe(db, status=RecipeStatus.PENDING)
    res = client.get(f"/api/recipes/{ok.id}")
    assert res.status_code == 200
    assert res.json()["ingredients"][0]["name"] == "bar"
    assert client.get(f"/api/recipes/{hidden.id}").status_code == 404


def test_submit_creates_pending_recipe(client: TestClient, db: Session) -> None:
    res = client.post("/api/recipes", data=form(), files={"image": ("x.png", PNG, "image/png")})
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "pending"
    assert body["image_url"] is None  # pending images are not public
    recipe = db.get(Recipe, body["id"])
    assert recipe is not None
    assert recipe.image_path is not None
    assert recipe.image_path.startswith("pending/")
    assert recipe.submitter_ip_hash
    assert client.get(f"/api/recipes/{body['id']}").status_code == 404


def test_submit_rejects_bad_image_and_bad_data(client: TestClient) -> None:
    bad_image = client.post(
        "/api/recipes", data=form(), files={"image": ("x.png", b"nope", "image/png")}
    )
    assert bad_image.status_code == 422
    assert client.post("/api/recipes", data=form(ingredients="not json")).status_code == 422
    assert client.post("/api/recipes", data=form(servings=0)).status_code == 422


def test_submit_rejects_oversize_image(client: TestClient, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(get_settings(), "max_image_bytes", 16)
    res = client.post("/api/recipes", data=form(), files={"image": ("x.png", PNG, "image/png")})
    assert res.status_code == 422


def test_submit_rate_limited_per_ip(client: TestClient, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(get_settings(), "max_submissions_per_day", 2)
    assert client.post("/api/recipes", data=form()).status_code == 201
    assert client.post("/api/recipes", data=form()).status_code == 201
    assert client.post("/api/recipes", data=form()).status_code == 429


def test_submit_with_unknown_source_recipe(client: TestClient) -> None:
    res = client.post(
        "/api/recipes", data=form(source_recipe_id="00000000-0000-0000-0000-000000000000")
    )
    assert res.status_code == 422


def test_get_recipe_scales_servings(client: TestClient, db: Session) -> None:
    recipe = make_recipe(db)  # 4 servings, bar 2 g
    body = client.get(f"/api/recipes/{recipe.id}?servings=8").json()
    assert body["servings"] == 8
    assert body["ingredients"][0]["quantity"] == 4.0
    assert client.get(f"/api/recipes/{recipe.id}?servings=0").status_code == 422


def test_list_recipes_pagination_and_total(client: TestClient, db: Session) -> None:
    for i in range(3):
        make_recipe(db, title=f"foo {i}")
    res = client.get("/api/recipes?limit=2&offset=2")
    assert len(res.json()) == 1
    assert res.headers["x-total-count"] == "3"


def test_submit_without_description_is_allowed(client: TestClient) -> None:
    ingredient = '[{"name":"bar","quantity":null,"unit":null,"note":null}]'
    form = {
        "lang": "he",
        "title": "foo",
        "servings": "2",
        "prep_minutes": "5",
        "difficulty": "easy",
        "kashrut": "parve",
        "ingredients": ingredient,
        "steps": '["baz"]',
    }
    res = client.post("/api/recipes", data=form)
    assert res.status_code == 201
    assert res.json()["description"] == ""
