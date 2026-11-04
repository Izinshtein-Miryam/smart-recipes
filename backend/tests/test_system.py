from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Role
from app.services.ai.client import MockLLMClient
from tests.conftest import login_as, make_user


def test_create_and_manage_content_manager(client: TestClient, seeded_db: Session) -> None:
    login_as(client, seeded_db, Role.SYSADMIN)
    body = {"email": "CM@example.com", "password": "password123", "display_name": "foo"}
    res = client.post("/api/system/users", json=body)
    assert res.status_code == 201
    cm = res.json()
    assert (cm["email"], cm["role"]) == ("cm@example.com", "content_manager")
    assert client.post("/api/system/users", json=body).status_code == 409

    assert (
        client.patch(f"/api/system/users/{cm['id']}", json={"is_active": False}).json()["is_active"]
        is False
    )
    assert len(client.get("/api/system/users", params={"role": "content_manager"}).json()) == 1
    assert len(client.get("/api/system/users", params={"q": "cm@"}).json()) == 1
    assert client.delete(f"/api/system/users/{cm['id']}").status_code == 204
    assert client.delete(f"/api/system/users/{cm['id']}").status_code == 404


def test_cannot_modify_self_or_other_sysadmins(client: TestClient, seeded_db: Session) -> None:
    other = make_user(seeded_db, "other@example.com", Role.SYSADMIN)
    me = login_as(client, seeded_db, Role.SYSADMIN)
    assert client.patch(f"/api/system/users/{me.id}", json={"is_active": False}).status_code == 403
    assert client.delete(f"/api/system/users/{other.id}").status_code == 403
    user = make_user(seeded_db, "u@example.com")
    bad_role = client.patch(f"/api/system/users/{user.id}", json={"role": "sysadmin"})
    assert bad_role.status_code == 422


def test_disabled_user_cannot_use_session(client: TestClient, seeded_db: Session) -> None:
    user = login_as(client, seeded_db)
    user.is_active = False
    seeded_db.commit()
    assert client.get("/api/auth/me").status_code == 401


def test_settings_roundtrip_and_quota_effect(
    client: TestClient, seeded_db: Session, llm: MockLLMClient
) -> None:
    login_as(client, seeded_db, Role.SYSADMIN)
    settings = client.get("/api/system/settings").json()
    assert settings["quotas"]["guest_daily_generations"] == 3
    assert settings["recommendation_weights"] == {"similarity": 0.6, "time": 0.3, "popularity": 0.1}

    settings["quotas"]["ai_requests_per_minute"] = 1
    assert client.put("/api/system/settings", json=settings).status_code == 200
    assert client.get("/api/system/settings").json()["quotas"]["ai_requests_per_minute"] == 1

    assert client.post("/api/search/smart", json={"query": "foo"}).status_code == 200
    assert client.post("/api/search/smart", json={"query": "foo"}).status_code == 429

    settings["recommendation_weights"] = {"similarity": 0, "time": 0, "popularity": 0}
    assert client.put("/api/system/settings", json=settings).status_code == 422


def test_stats_and_audit(client: TestClient, seeded_db: Session) -> None:
    login_as(client, seeded_db, Role.SYSADMIN)
    client.post("/api/search/smart", json={"query": "foo"})  # AI unavailable -> error call
    client.get("/api/recipes/salat-kinoa")
    client.put("/api/system/settings", json=client.get("/api/system/settings").json())

    stats = client.get("/api/system/stats", params={"days": 7}).json()
    search = next(f for f in stats["ai_by_feature"] if f["feature"] == "search")
    assert (search["calls"], search["errors"]) == (1, 1)
    assert stats["popular_recipes"][0]["slug"] == "salat-kinoa"
    assert stats["users_by_role"] == {"sysadmin": 1}
    assert stats["recipes_by_status"] == {"published": 3}

    audit = client.get("/api/system/audit").json()
    assert audit["total"] == 1
    assert audit["items"][0]["action"] == "settings.update"
    assert client.get("/api/system/audit", params={"action": "foo"}).json()["total"] == 0
