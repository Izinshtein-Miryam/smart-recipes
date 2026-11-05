import os
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

# Settings are read at import time, so configure the environment before importing `app`.
TEST_DB = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://recipes:recipes@localhost:5432/recipes_test"
)
os.environ["DATABASE_URL"] = TEST_DB
os.environ["STORAGE_DIR"] = tempfile.mkdtemp(prefix="recipes-test-")
os.environ["JWT_SECRET"] = "lorem-ipsum-test-secret"
os.environ["OPENAI_API_KEY"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

import app.models  # noqa: E402, F401
from app.config import get_settings  # noqa: E402
from app.core.deps import get_ai_service  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Recipe, RecipeStatus  # noqa: E402
from app.schemas.ai import AdaptedRecipe, FridgeMatch, NutritionEstimate  # noqa: E402
from app.services.ai_service import AiUnavailableError  # noqa: E402

ADMIN_PASSWORD = "lorem-ipsum"


class FakeAi:
    """Stands in for AiService: canned answers, no network."""

    def __init__(self) -> None:
        self.fail = False

    def _check(self) -> None:
        if self.fail:
            raise AiUnavailableError("boom")

    def fridge_search(
        self, db: Session, ingredients: list[str], candidates: list[Recipe]
    ) -> list[FridgeMatch]:
        self._check()
        return [
            FridgeMatch(
                recipe_id=str(candidates[0].id), match_score=80, missing_ingredients=["baz"]
            )
        ]

    def estimate_nutrition(self, db: Session, recipe: Recipe) -> NutritionEstimate:
        self._check()
        return NutritionEstimate(calories=100, protein_g=1, carbs_g=2, fat_g=3, confidence="medium")

    def chat_stream(
        self, db: Session, recipe: Recipe, message: str, previous_response_id: str | None
    ) -> Iterator[dict[str, Any]]:
        yield {"event": "text_delta", "data": {"text": "Lorem"}}
        yield {"event": "done", "data": {"response_id": "resp_foo"}}

    def adapt_recipe(self, db: Session, recipe: Recipe, instruction: str) -> AdaptedRecipe:
        self._check()
        return AdaptedRecipe(
            title="foo adapted",
            description="Lorem ipsum",
            servings=recipe.servings,
            prep_minutes=recipe.prep_minutes,
            difficulty=recipe.difficulty,
            equipment=recipe.equipment,
            kashrut=recipe.kashrut,
            ingredients=recipe.ingredients,
            steps=recipe.steps,
            changes_summary=["foo"],
            feasible=True,
            reason=None,
        )


@pytest.fixture(scope="session", autouse=True)
def _schema() -> Iterator[None]:
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    Base.metadata.create_all(engine)
    yield


@pytest.fixture(autouse=True)
def _clean(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(get_settings(), "admin_password_hash", hash_password(ADMIN_PASSWORD))
    yield
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE recipes, ai_usage_log CASCADE"))
    for f in Path(os.environ["STORAGE_DIR"]).rglob("*.*"):
        f.unlink()


@pytest.fixture
def db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


@pytest.fixture
def fake_ai() -> FakeAi:
    return FakeAi()


@pytest.fixture
def client(fake_ai: FakeAi) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_ai_service] = lambda: fake_ai
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    res = client.post("/api/admin/login", json={"password": ADMIN_PASSWORD})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def make_recipe(db: Session, **overrides: object) -> Recipe:
    values: dict[str, object] = {
        "lang": "he",
        "title": "foo",
        "description": "Lorem ipsum dolor sit amet",
        "servings": 4,
        "prep_minutes": 30,
        "difficulty": "easy",
        "equipment": ["oven"],
        "kashrut": "parve",
        "ingredients": [{"name": "bar", "quantity": 2, "unit": "g", "note": None}],
        "steps": ["baz"],
        "status": RecipeStatus.APPROVED,
    }
    recipe = Recipe(**{**values, **overrides})
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe
