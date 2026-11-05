from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AICall, AIFeature, AuditLog, Recipe, Role, User
from tests.conftest import login, make_user


@pytest.fixture
def admin(client: TestClient, seeded_db: Session) -> User:
    user = make_user(seeded_db, "root@example.com", Role.SYSADMIN)
    login(client, "root@example.com")
    return user


def _audit(db: Session, action: str) -> list[AuditLog]:
    db.expire_all()
    return list(db.scalars(select(AuditLog).where(AuditLog.action == action)))


def _new_cm(client: TestClient, email: str = "cm@example.com") -> dict[str, Any]:
    res = client.post(
        "/api/system/users",
        json={"email": email, "password": "password123", "display_name": "foo"},
    )
    assert res.status_code == 201
    body: dict[str, Any] = res.json()
    return body


ENDPOINTS = [
    ("GET", "/api/system/users"),
    ("POST", "/api/system/users"),
    ("PATCH", "/api/system/users/1"),
    ("DELETE", "/api/system/users/1"),
    ("GET", "/api/system/settings"),
    ("PUT", "/api/system/settings"),
    ("GET", "/api/system/stats"),
    ("GET", "/api/system/audit"),
]


@pytest.mark.parametrize(("method", "path"), ENDPOINTS)
def test_anonymous_gets_401(client: TestClient, method: str, path: str) -> None:
    assert client.request(method, path).status_code == 401


@pytest.mark.parametrize("role", [Role.USER, Role.CONTENT_MANAGER])
@pytest.mark.parametrize(("method", "path"), ENDPOINTS)
def test_non_sysadmin_gets_403(
    client: TestClient, seeded_db: Session, role: Role, method: str, path: str
) -> None:
    make_user(seeded_db, "x@example.com", role)
    login(client, "x@example.com")
    assert client.request(method, path).status_code == 403


@pytest.mark.usefixtures("admin")
def test_create_content_manager_and_login(client: TestClient, seeded_db: Session) -> None:
    body = _new_cm(client, "CM@Example.com")
    assert body["role"] == "content_manager"
    assert body["email"] == "cm@example.com"
    assert "password_hash" not in body
    entries = _audit(seeded_db, "user.create")
    assert len(entries) == 1
    assert entries[0].entity_id == str(body["id"])
    assert entries[0].details["email"] == "cm@example.com"

    client.post("/api/auth/logout")
    login(client, "cm@example.com")
    assert client.get("/api/admin/recipes").status_code == 200
    assert client.get("/api/system/users").status_code == 403


@pytest.mark.usefixtures("admin")
def test_create_user_rejections(client: TestClient) -> None:
    _new_cm(client)
    base = {"email": "cm@example.com", "password": "password123", "display_name": "foo"}
    assert client.post("/api/system/users", json=base).status_code == 409
    for override in ({"role": "sysadmin"}, {"role": "user"}, {"password": "short"}):
        res = client.post("/api/system/users", json={**base, "email": "n@example.com", **override})
        assert res.status_code == 422


@pytest.mark.usefixtures("admin")
def test_list_users_filters(client: TestClient, seeded_db: Session) -> None:
    _new_cm(client)
    make_user(seeded_db, "plain@example.com")
    assert client.get("/api/system/users").json()["total"] == 3
    only_cm = client.get("/api/system/users", params={"role": "content_manager"}).json()
    assert [u["email"] for u in only_cm["items"]] == ["cm@example.com"]
    assert client.get("/api/system/users", params={"q": "plain"}).json()["total"] == 1
    paged = client.get("/api/system/users", params={"page_size": 2, "page": 2}).json()
    assert len(paged["items"]) == 1


@pytest.mark.usefixtures("admin")
def test_deactivate_and_reactivate(client: TestClient, seeded_db: Session) -> None:
    cm = _new_cm(client)
    res = client.patch(f"/api/system/users/{cm['id']}", json={"is_active": False})
    assert res.status_code == 200
    assert res.json()["is_active"] is False
    assert _audit(seeded_db, "user.update")[0].details == {"is_active": False}

    other = TestClient(client.app)
    credentials = {"email": "cm@example.com", "password": "password123"}
    assert other.post("/api/auth/login", json=credentials).status_code == 401

    res = client.patch(
        f"/api/system/users/{cm['id']}", json={"is_active": True, "display_name": "bar"}
    )
    assert res.json()["is_active"] is True
    assert res.json()["display_name"] == "bar"


@pytest.mark.usefixtures("admin")
def test_delete_user_keeps_recipes_and_audit(client: TestClient, seeded_db: Session) -> None:
    cm = _new_cm(client)
    client.post("/api/auth/logout")
    login(client, "cm@example.com")
    payload = {"title": "foo", "dish_type": "main", "difficulty": "easy"}
    rid = client.post("/api/admin/recipes", json=payload).json()["id"]
    client.post("/api/auth/logout")
    login(client, "root@example.com")

    assert client.delete(f"/api/system/users/{cm['id']}").status_code == 204
    seeded_db.expire_all()
    assert seeded_db.get(User, cm["id"]) is None
    recipe = seeded_db.get(Recipe, rid)
    assert recipe is not None
    assert recipe.owner_id is None
    entries = _audit(seeded_db, "user.delete")
    assert len(entries) == 1
    assert entries[0].details["email"] == "cm@example.com"
    created = _audit(seeded_db, "recipe.create")
    assert len(created) == 1
    assert created[0].actor_id is None


def test_protected_targets(client: TestClient, seeded_db: Session, admin: User) -> None:
    own = f"/api/system/users/{admin.id}"
    assert client.delete(own).status_code == 409
    assert client.patch(own, json={"is_active": False}).status_code == 409
    peer = make_user(seeded_db, "root2@example.com", Role.SYSADMIN)
    assert client.delete(f"/api/system/users/{peer.id}").status_code == 403
    peer_url = f"/api/system/users/{peer.id}"
    assert client.patch(peer_url, json={"is_active": False}).status_code == 403
    assert client.delete("/api/system/users/9999").status_code == 404
    assert client.patch("/api/system/users/9999", json={"is_active": False}).status_code == 404


@pytest.mark.usefixtures("admin")
def test_settings_defaults_and_update(client: TestClient, seeded_db: Session) -> None:
    defaults = client.get("/api/system/settings").json()
    assert defaults == {
        "guest_daily_quota": 3,
        "user_daily_quota": 20,
        "recommendation_weights": {"similarity": 0.6, "time": 0.3, "popularity": 0.1},
    }

    res = client.put("/api/system/settings", json={"user_daily_quota": 50})
    assert res.status_code == 200
    assert res.json()["user_daily_quota"] == 50
    assert res.json()["guest_daily_quota"] == 3

    weights = {"similarity": 0.5, "time": 0.25, "popularity": 0.25}
    res = client.put("/api/system/settings", json={"recommendation_weights": weights})
    assert res.json()["recommendation_weights"] == weights
    assert client.get("/api/system/settings").json()["user_daily_quota"] == 50

    entries = _audit(seeded_db, "settings.update")
    assert [(e.entity_id, e.details["to"]) for e in entries] == [
        ("user_daily_quota", 50),
        ("recommendation_weights", weights),
    ]
    assert entries[0].details["from"] == 20


@pytest.mark.usefixtures("admin")
def test_settings_validation(client: TestClient) -> None:
    bad = {"recommendation_weights": {"similarity": 0.5, "time": 0.5, "popularity": 0.5}}
    assert client.put("/api/system/settings", json=bad).status_code == 422
    assert client.put("/api/system/settings", json={"user_daily_quota": -1}).status_code == 422


@pytest.mark.usefixtures("admin")
def test_stats(client: TestClient, seeded_db: Session) -> None:
    seeded_db.add_all(
        [
            AICall(
                feature=AIFeature.CHAT,
                model="foo",
                input_tokens=10,
                output_tokens=5,
                cost_usd=0.25,
                status="ok",
            ),
            AICall(
                feature=AIFeature.CHAT,
                model="foo",
                input_tokens=1,
                output_tokens=2,
                cost_usd=0.5,
                status="ok",
            ),
            AICall(feature=AIFeature.IMAGE, model="bar", status="error"),
        ]
    )
    popular = seeded_db.scalars(select(Recipe).where(Recipe.slug == "salat-kinoa")).one()
    popular.view_count = 42
    seeded_db.commit()

    body = client.get("/api/system/stats").json()
    assert body["users"] == 1
    assert body["recipes"] == seeded_db.scalar(select(func.count()).select_from(Recipe))
    assert body["ai_calls"] == 3
    assert body["ai_cost_usd"] == pytest.approx(0.75)
    chat = next(u for u in body["ai_usage"] if u["feature"] == "chat")
    assert (chat["calls"], chat["input_tokens"], chat["output_tokens"]) == (2, 11, 7)
    assert body["popular_recipes"][0]["slug"] == "salat-kinoa"
    assert body["popular_recipes"][0]["view_count"] == 42
    limited = client.get("/api/system/stats", params={"popular_limit": 1}).json()
    assert len(limited["popular_recipes"]) == 1


@pytest.mark.usefixtures("admin")
def test_audit_listing_and_filters(client: TestClient) -> None:
    cm = _new_cm(client)
    client.patch(f"/api/system/users/{cm['id']}", json={"is_active": False})
    client.put("/api/system/settings", json={"guest_daily_quota": 1})

    body = client.get("/api/system/audit").json()
    assert body["total"] == 3
    actions = [e["action"] for e in body["items"]]
    assert actions == ["settings.update", "user.update", "user.create"]
    assert body["items"][0]["actor_id"] is not None

    assert client.get("/api/system/audit", params={"entity_type": "user"}).json()["total"] == 2
    one = client.get("/api/system/audit", params={"action": "user.create"}).json()
    assert one["total"] == 1
    assert one["items"][0]["entity_id"] == str(cm["id"])
    assert client.get("/api/system/audit", params={"actor_id": 99999}).json()["total"] == 0
    page = client.get("/api/system/audit", params={"page_size": 2, "page": 2}).json()
    assert len(page["items"]) == 1
