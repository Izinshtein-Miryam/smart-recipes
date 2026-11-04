import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.config import get_settings
from app.core.providers import get_llm_client, get_rate_limiter
from app.core.security import hash_password
from app.db import Base, get_db, make_engine
from app.main import create_app
from app.models import Role, User
from app.seed import seed
from app.services.ai.client import MockLLMClient
from app.services.limits import RateLimiter


@pytest.fixture(autouse=True)
def fast_hashing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "bcrypt_rounds", 4)


@pytest.fixture
def db() -> Iterator[Session]:
    engine = make_engine("sqlite://")
    engine.pool = StaticPool(engine.pool._creator)  # single shared in-memory connection
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_factory() as session:
        yield session
    engine.dispose()


@pytest.fixture
def seeded_db(db: Session) -> Session:
    seed(db)
    return db


@pytest.fixture
def llm() -> MockLLMClient:
    """Scripted LLM. Tests set `llm.responses`; empty means "AI unavailable"."""
    return MockLLMClient()


@pytest.fixture
def media_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(get_settings(), "media_dir", tmp_path)
    return tmp_path


@pytest.fixture
def client(seeded_db: Session, llm: MockLLMClient, media_dir: Path) -> Iterator[TestClient]:
    app = create_app()
    limiter = RateLimiter()
    app.dependency_overrides[get_db] = lambda: seeded_db
    app.dependency_overrides[get_llm_client] = lambda: llm
    app.dependency_overrides[get_rate_limiter] = lambda: limiter
    with TestClient(app) as c:
        yield c


def make_user(db: Session, email: str, role: Role = Role.USER) -> User:
    user = User(
        email=email, password_hash=hash_password("password123"), display_name="foo", role=role
    )
    db.add(user)
    db.commit()
    return user


def login(client: TestClient, email: str) -> None:
    res = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert res.status_code == 200


def login_as(client: TestClient, db: Session, role: Role = Role.USER, email: str = "") -> User:
    email = email or f"{role.value}@example.com"
    user = make_user(db, email, role)
    login(client, email)
    return user


def parse_sse(text: str) -> list[tuple[str, Any]]:
    events: list[tuple[str, Any]] = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events
