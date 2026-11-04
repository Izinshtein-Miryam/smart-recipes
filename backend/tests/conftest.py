from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.security import hash_password
from app.db import Base, get_db, make_engine
from app.main import create_app
from app.models import Role, User
from app.seed import seed


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
def client(seeded_db: Session) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: seeded_db
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
