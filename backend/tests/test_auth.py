from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Role
from tests.conftest import login, make_user


def test_register_sets_cookie_and_me(client: TestClient) -> None:
    res = client.post(
        "/api/auth/register",
        json={"email": "Foo@Example.com", "password": "password123", "display_name": "foo"},
    )
    assert res.status_code == 201
    assert res.json()["email"] == "foo@example.com"
    assert res.json()["role"] == "user"
    assert client.get("/api/auth/me").json()["display_name"] == "foo"


def test_register_duplicate_email(client: TestClient, seeded_db: Session) -> None:
    make_user(seeded_db, "bar@example.com")
    res = client.post(
        "/api/auth/register",
        json={"email": "bar@example.com", "password": "password123", "display_name": "bar"},
    )
    assert res.status_code == 409


def test_register_short_password(client: TestClient) -> None:
    res = client.post(
        "/api/auth/register",
        json={"email": "baz@example.com", "password": "short", "display_name": "baz"},
    )
    assert res.status_code == 422


def test_login_wrong_password(client: TestClient, seeded_db: Session) -> None:
    make_user(seeded_db, "foo@example.com")
    res = client.post("/api/auth/login", json={"email": "foo@example.com", "password": "nope"})
    assert res.status_code == 401


def test_inactive_user_cannot_login(client: TestClient, seeded_db: Session) -> None:
    user = make_user(seeded_db, "foo@example.com")
    user.is_active = False
    seeded_db.commit()
    res = client.post(
        "/api/auth/login", json={"email": "foo@example.com", "password": "password123"}
    )
    assert res.status_code == 401


def test_logout_clears_session(client: TestClient, seeded_db: Session) -> None:
    make_user(seeded_db, "foo@example.com")
    login(client, "foo@example.com")
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_invalid_token(client: TestClient) -> None:
    client.cookies.set("access_token", "garbage")
    assert client.get("/api/auth/me").status_code == 401


def test_role_guards(client: TestClient, seeded_db: Session) -> None:
    make_user(seeded_db, "user@example.com")
    make_user(seeded_db, "cm@example.com", Role.CONTENT_MANAGER)
    make_user(seeded_db, "sys@example.com", Role.SYSADMIN)

    assert client.get("/api/system/users").status_code == 401

    login(client, "user@example.com")
    assert client.post("/api/admin/recipes").status_code == 403

    login(client, "cm@example.com")
    assert client.post("/api/admin/recipes").status_code == 422  # allowed, empty body rejected
    assert client.get("/api/system/users").status_code == 403

    login(client, "sys@example.com")
    assert client.get("/api/system/users").status_code == 200
