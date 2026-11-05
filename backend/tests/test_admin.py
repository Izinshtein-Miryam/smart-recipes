import io
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.admin import get_image_provider, get_media_dir
from app.models import AICall, AuditLog, Ingredient, KosherType, Recipe, RecipeStatus, Role
from app.services.images.provider import MockImageProvider
from tests.conftest import login, make_user


@pytest.fixture
def media(client: TestClient, tmp_path: Path) -> Iterator[Path]:
    overrides = client.app.dependency_overrides  # type: ignore[attr-defined]
    overrides[get_media_dir] = lambda: tmp_path
    overrides[get_image_provider] = MockImageProvider
    yield tmp_path


@pytest.fixture
def manager(client: TestClient, seeded_db: Session) -> None:
    make_user(seeded_db, "cm@example.com", Role.CONTENT_MANAGER)
    login(client, "cm@example.com")


def _ingredient_id(db: Session, kosher: KosherType) -> int:
    ing = db.scalars(select(Ingredient).where(Ingredient.kosher_type == kosher)).first()
    assert ing is not None
    return ing.id


def _payload(db: Session, **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "title": "Lorem ipsum",
        "description": "dolor sit amet",
        "dish_type": "main",
        "difficulty": "easy",
        "prep_minutes": 5,
        "cook_minutes": 10,
        "servings": 2,
        "ingredients": [
            {"ingredient_id": _ingredient_id(db, KosherType.PARVE), "quantity": 1, "unit": "foo"}
        ],
        "steps": [{"text": "foo", "timer_seconds": 30}],
    }
    body.update(overrides)
    return body


def _image_bytes(fmt: str = "PNG") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (20, 20), (200, 10, 10)).save(buf, format=fmt)
    return buf.getvalue()


def _audit(db: Session, action: str) -> list[AuditLog]:
    db.expire_all()
    return list(db.scalars(select(AuditLog).where(AuditLog.action == action)))


ENDPOINTS = [
    ("GET", "/api/admin/recipes"),
    ("GET", "/api/admin/recipes/1"),
    ("POST", "/api/admin/recipes"),
    ("PUT", "/api/admin/recipes/1"),
    ("PATCH", "/api/admin/recipes/1/status"),
    ("DELETE", "/api/admin/recipes/1"),
    ("POST", "/api/admin/recipes/1/images"),
    ("PATCH", "/api/admin/recipes/1/images/1"),
]


@pytest.mark.parametrize(("method", "path"), ENDPOINTS)
def test_anonymous_gets_401(client: TestClient, method: str, path: str) -> None:
    assert client.request(method, path).status_code == 401


@pytest.mark.parametrize(("method", "path"), ENDPOINTS)
def test_regular_user_gets_403(
    client: TestClient, seeded_db: Session, method: str, path: str
) -> None:
    make_user(seeded_db, "u@example.com")
    login(client, "u@example.com")
    assert client.request(method, path).status_code == 403


def test_sysadmin_allowed(client: TestClient, seeded_db: Session) -> None:
    make_user(seeded_db, "root@example.com", Role.SYSADMIN)
    login(client, "root@example.com")
    assert client.get("/api/admin/recipes").status_code == 200


@pytest.mark.usefixtures("manager")
def test_create_get_and_list(client: TestClient, seeded_db: Session) -> None:
    res = client.post("/api/admin/recipes", json=_payload(seeded_db))
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "draft"
    assert body["kosher_type"] == "parve"
    assert body["slug"] == "lorem-ipsum"
    assert body["steps"][0]["order"] == 1
    assert client.get("/api/recipes/lorem-ipsum").status_code == 404  # draft is not public

    again = client.post("/api/admin/recipes", json=_payload(seeded_db)).json()
    assert again["slug"] == "lorem-ipsum-2"

    assert client.get(f"/api/admin/recipes/{body['id']}").json()["title"] == "Lorem ipsum"
    listing = client.get("/api/admin/recipes", params={"q": "Lorem", "status": "draft"}).json()
    assert listing["total"] == 2
    assert client.get("/api/admin/recipes").json()["total"] == 5

    entries = _audit(seeded_db, "recipe.create")
    assert len(entries) == 2
    assert entries[0].entity_type == "recipe"
    assert entries[0].entity_id == str(body["id"])
    assert entries[0].actor_id is not None


@pytest.mark.usefixtures("manager")
def test_kosher_type_derived_and_mix_rejected(client: TestClient, seeded_db: Session) -> None:
    meat = _ingredient_id(seeded_db, KosherType.MEAT)
    dairy = _ingredient_id(seeded_db, KosherType.DAIRY)
    ok = client.post(
        "/api/admin/recipes", json=_payload(seeded_db, ingredients=[{"ingredient_id": meat}])
    )
    assert ok.json()["kosher_type"] == "meat"
    mix = client.post(
        "/api/admin/recipes",
        json=_payload(seeded_db, ingredients=[{"ingredient_id": meat}, {"ingredient_id": dairy}]),
    )
    assert mix.status_code == 422


@pytest.mark.usefixtures("manager")
def test_validation_errors(client: TestClient, seeded_db: Session) -> None:
    unknown = _payload(seeded_db, ingredients=[{"ingredient_id": 99999}])
    assert client.post("/api/admin/recipes", json=unknown).status_code == 422
    empty_publish = _payload(seeded_db, ingredients=[], status="published")
    assert client.post("/api/admin/recipes", json=empty_publish).status_code == 422
    assert client.post("/api/admin/recipes", json={"title": ""}).status_code == 422


@pytest.mark.usefixtures("manager")
def test_update_publish_hide_delete(client: TestClient, seeded_db: Session) -> None:
    rid = client.post("/api/admin/recipes", json=_payload(seeded_db)).json()["id"]

    res = client.put(
        f"/api/admin/recipes/{rid}",
        json=_payload(seeded_db, title="Foo bar", status="published"),
    )
    assert res.status_code == 200
    assert res.json()["title"] == "Foo bar"
    assert res.json()["slug"] == "lorem-ipsum"  # slug stays stable
    assert client.get("/api/recipes/lorem-ipsum").status_code == 200

    hidden = client.patch(f"/api/admin/recipes/{rid}/status", json={"status": "hidden"})
    assert hidden.json()["status"] == "hidden"
    assert client.get("/api/recipes/lorem-ipsum").status_code == 404
    published = client.patch(f"/api/admin/recipes/{rid}/status", json={"status": "published"})
    assert published.json()["status"] == "published"

    assert client.delete(f"/api/admin/recipes/{rid}").status_code == 204
    assert client.get(f"/api/admin/recipes/{rid}").status_code == 404
    assert client.delete(f"/api/admin/recipes/{rid}").status_code == 404
    assert client.put(f"/api/admin/recipes/{rid}", json=_payload(seeded_db)).status_code == 404

    assert len(_audit(seeded_db, "recipe.update")) == 1
    status_entries = _audit(seeded_db, "recipe.status")
    assert [e.details["to"] for e in status_entries] == ["hidden", "published"]
    assert len(_audit(seeded_db, "recipe.delete")) == 1


@pytest.mark.usefixtures("manager")
def test_publish_empty_draft_via_status_rejected(client: TestClient, seeded_db: Session) -> None:
    rid = client.post(
        "/api/admin/recipes", json=_payload(seeded_db, ingredients=[], steps=[])
    ).json()["id"]
    res = client.patch(f"/api/admin/recipes/{rid}/status", json={"status": "published"})
    assert res.status_code == 422
    seeded_db.expire_all()
    recipe = seeded_db.get(Recipe, rid)
    assert recipe is not None
    assert recipe.status == RecipeStatus.DRAFT


@pytest.mark.usefixtures("manager")
def test_image_flow(client: TestClient, seeded_db: Session, media: Path) -> None:
    rid = client.post("/api/admin/recipes", json=_payload(seeded_db)).json()["id"]
    url = f"/api/admin/recipes/{rid}/images"
    png = ("a.png", _image_bytes(), "image/png")

    up = client.post(url, files={"file": png})
    assert up.status_code == 201
    assert up.json()["origin"] == "upload"
    assert up.json()["processed_path"] is None
    assert (media / up.json()["original_path"]).exists()

    edit = client.post(url, data={"action": "edit", "prompt": "foo"}, files={"file": png})
    assert edit.json()["origin"] == "ai_edit"
    assert edit.json()["original_path"]
    assert edit.json()["processed_path"]
    assert edit.json()["approved"] is False

    gen = client.post(url, data={"action": "generate"})
    assert gen.status_code == 201
    assert gen.json()["origin"] == "ai_generate"
    assert gen.json()["original_path"] is None
    assert (media / gen.json()["processed_path"]).exists()
    assert len(_audit(seeded_db, "image.create")) == 3
    assert len(seeded_db.scalars(select(AICall)).all()) == 2

    gid, eid = gen.json()["id"], edit.json()["id"]
    assert client.patch(f"{url}/{gid}", json={"is_primary": True}).status_code == 409
    approved = client.patch(f"{url}/{gid}", json={"approved": True, "is_primary": True})
    assert approved.json()["is_primary"] is True
    client.patch(f"{url}/{eid}", json={"approved": True, "is_primary": True})
    detail = client.get(f"/api/admin/recipes/{rid}").json()
    assert [i["id"] for i in detail["images"] if i["is_primary"]] == [eid]
    assert client.patch(f"{url}/9999", json={"approved": True}).status_code == 404
    assert len(_audit(seeded_db, "image.update")) == 2

    assert client.delete(f"/api/admin/recipes/{rid}").status_code == 204
    assert not (media / "recipes" / str(rid)).exists()


@pytest.mark.usefixtures("manager", "media")
def test_image_validation(client: TestClient, seeded_db: Session) -> None:
    rid = client.post("/api/admin/recipes", json=_payload(seeded_db)).json()["id"]
    url = f"/api/admin/recipes/{rid}/images"
    assert client.post(url).status_code == 422  # upload without a file
    bad = client.post(url, files={"file": ("a.png", b"not an image", "image/png")})
    assert bad.status_code == 422
    gif = client.post(url, files={"file": ("a.gif", _image_bytes("GIF"), "image/gif")})
    assert gif.status_code == 422
    missing = client.post("/api/admin/recipes/9999/images", data={"action": "generate"})
    assert missing.status_code == 404


@pytest.mark.usefixtures("manager", "media")
def test_image_provider_failure_is_502(client: TestClient, seeded_db: Session) -> None:
    class Broken(MockImageProvider):
        async def generate(self, prompt: str) -> bytes:
            raise RuntimeError("boom")

    client.app.dependency_overrides[get_image_provider] = Broken  # type: ignore[attr-defined]
    rid = client.post("/api/admin/recipes", json=_payload(seeded_db)).json()["id"]
    res = client.post(f"/api/admin/recipes/{rid}/images", data={"action": "generate"})
    assert res.status_code == 502
    assert seeded_db.scalars(select(AICall)).one().status == "error"
