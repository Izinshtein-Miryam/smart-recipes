import json
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AICall, Ingredient, Recipe, Role
from app.services.ai.client import MockLLMClient
from tests.conftest import login_as, parse_sse


def recipe_json(**overrides: Any) -> str:
    base: dict[str, Any] = {
        "title": "חביתת תרד",
        "description": "חביתה ירוקה ומהירה",
        "servings": 2,
        "prep_minutes": 5,
        "cook_minutes": 10,
        "difficulty": "easy",
        "dish_type": "main",
        "kosher_type": "parve",
        "diet_tags": ["gluten_free"],
        "time_tags": ["morning"],
        "ingredients": [
            {
                "name": "ביצים",
                "quantity": 3,
                "unit": "יחידות",
                "kosher_type": "parve",
                "note": None,
            },
            {"name": "תרד", "quantity": 100, "unit": "גרם", "kosher_type": "parve", "note": None},
            {"name": "מלח", "quantity": 0.5, "unit": "כפית", "kosher_type": "parve", "note": None},
        ],
        "steps": [
            {"text": "טורפים את הביצים עם התרד.", "timer_seconds": None},
            {"text": "מטגנים במחבת.", "timer_seconds": 300},
        ],
        "changes": [],
    }
    base.update(overrides)
    return json.dumps(base, ensure_ascii=False)


INGREDIENTS_REQUEST = {"mode": "ingredients", "ingredients": ["ביצים", "תרד"], "servings": 2}


def generate(client: TestClient, body: dict[str, Any]) -> list[tuple[str, Any]]:
    res = client.post("/api/generate", json=body)
    assert res.status_code == 200, res.text
    return parse_sse(res.text)


def test_generate_from_ingredients(client: TestClient, llm: MockLLMClient) -> None:
    llm.responses = [recipe_json()]
    events = generate(client, INGREDIENTS_REQUEST)
    kinds = [e for e, _ in events]
    assert kinds[0] == "attempt"
    assert "delta" in kinds
    event, done = events[-1]
    assert event == "done"
    recipe = done["recipe"]
    assert recipe["kosher_type"] == "parve"
    salt = next(i for i in recipe["ingredients"] if i["name"] == "מלח")
    eggs = next(i for i in recipe["ingredients"] if i["name"] == "ביצים")
    assert salt["not_provided"] is True
    assert eggs["not_provided"] is False
    assert eggs["ingredient_id"] is not None
    assert done["remaining"] == 2  # guest quota 3
    assert "ביצים, תרד" in llm.calls[0]["messages"][0]["content"]


def test_generate_rejects_meat_dairy_mix_then_retries(
    client: TestClient, llm: MockLLMClient
) -> None:
    mixed = json.loads(recipe_json())
    mixed["ingredients"] += [
        {"name": "חזה עוף", "quantity": 200, "unit": "גרם", "kosher_type": "meat", "note": None},
        {
            "name": "גבינה בולגרית",
            "quantity": 50,
            "unit": "גרם",
            "kosher_type": "dairy",
            "note": None,
        },
    ]
    llm.responses = [json.dumps(mixed), recipe_json()]
    events = generate(client, {"mode": "free_text", "text": "ארוחה מהירה"})
    retry = next(d for e, d in events if e == "retry")
    assert "בשריים וחלביים" in retry["reason"]
    assert events[-1][0] == "done"
    # The retry prompt includes the rejected answer and the reason.
    assert len(llm.calls[1]["messages"]) == 3


def test_generate_rejects_non_basic_extra_ingredient(
    client: TestClient, llm: MockLLMClient
) -> None:
    extra = json.loads(recipe_json())
    extra["ingredients"].append(
        {"name": "חזה עוף", "quantity": 200, "unit": "גרם", "kosher_type": "meat", "note": None}
    )
    llm.responses = [json.dumps(extra)]
    events = generate(client, INGREDIENTS_REQUEST)
    assert [e for e, _ in events].count("attempt") == 2
    assert events[-1][0] == "error"


def test_generate_rejects_wrong_kosher_type(client: TestClient, llm: MockLLMClient) -> None:
    dairy = json.loads(recipe_json())
    dairy["ingredients"].append(
        {
            "name": "גבינה בולגרית",
            "quantity": 50,
            "unit": "גרם",
            "kosher_type": "dairy",
            "note": None,
        }
    )
    llm.responses = [json.dumps(dairy), recipe_json()]
    events = generate(client, {"mode": "free_text", "text": "foo", "kosher_type": "meat"})
    assert any(e == "retry" for e, _ in events)
    assert events[-1][1]["recipe"]["kosher_type"] == "parve"


def test_generate_schema_violation_fails_after_retry(
    client: TestClient, llm: MockLLMClient
) -> None:
    llm.responses = [recipe_json(steps=[]), recipe_json(ingredients=[])]
    events = generate(client, {"mode": "free_text", "text": "foo"})
    assert events[-1][0] == "error"


def test_generate_reports_ai_unavailable(client: TestClient) -> None:
    events = generate(client, {"mode": "free_text", "text": "foo"})
    assert events[-1][0] == "error"


def test_generate_validates_mode_fields(client: TestClient) -> None:
    assert client.post("/api/generate", json={"mode": "ingredients"}).status_code == 422
    assert client.post("/api/generate", json={"mode": "free_text"}).status_code == 422
    assert client.post("/api/generate", json={"mode": "adapt", "text": "foo"}).status_code == 422


def test_guest_daily_quota(client: TestClient, llm: MockLLMClient) -> None:
    llm.responses = [recipe_json()]
    for _ in range(3):
        assert generate(client, {"mode": "free_text", "text": "foo"})[-1][0] == "done"
    res = client.post("/api/generate", json={"mode": "free_text", "text": "foo"})
    assert res.status_code == 429


def test_content_manager_has_no_quota(
    client: TestClient, llm: MockLLMClient, seeded_db: Session
) -> None:
    login_as(client, seeded_db, Role.CONTENT_MANAGER)
    llm.responses = [recipe_json()]
    done = generate(client, {"mode": "free_text", "text": "foo"})[-1][1]
    assert done["remaining"] is None


def test_adapt_mode_includes_recipe_and_changes(client: TestClient, llm: MockLLMClient) -> None:
    llm.responses = [recipe_json(changes=["הוחלפה הגבינה בטופו"])]
    events = generate(
        client, {"mode": "adapt", "recipe_slug": "shakshuka-yeruka", "text": "בלי גבינה"}
    )
    assert events[-1][1]["recipe"]["changes"] == ["הוחלפה הגבינה בטופו"]
    prompt = llm.calls[0]["messages"][0]["content"]
    assert "שקשוקה ירוקה" in prompt
    assert "בלי גבינה" in prompt


def test_adapt_unknown_recipe(client: TestClient) -> None:
    res = client.post("/api/generate", json={"mode": "adapt", "recipe_slug": "foo", "text": "bar"})
    assert res.status_code == 404


def test_try_again_variation_in_prompt(client: TestClient, llm: MockLLMClient) -> None:
    llm.responses = [recipe_json()]
    generate(client, {"mode": "free_text", "text": "foo", "variation": 1})
    assert "גרסה מס' 2" in llm.calls[0]["messages"][0]["content"]


def test_save_generated_recipe(client: TestClient, llm: MockLLMClient, seeded_db: Session) -> None:
    unknown = json.loads(recipe_json())
    unknown["ingredients"].append(
        {"name": "עירית", "quantity": 1, "unit": "כף", "kosher_type": "parve", "note": "קצוצה"}
    )
    llm.responses = [json.dumps(unknown)]
    done = generate(client, {"mode": "free_text", "text": "foo"})[-1][1]

    assert client.post(f"/api/generate/{done['id']}/save").status_code == 401

    user = login_as(client, seeded_db)
    res = client.post(f"/api/generate/{done['id']}/save")
    assert res.status_code == 200
    slug = res.json()["slug"]
    assert slug.startswith("ai-")
    # Saving twice returns the same recipe.
    assert client.post(f"/api/generate/{done['id']}/save").json()["slug"] == slug

    recipe = seeded_db.scalar(select(Recipe).where(Recipe.slug == slug))
    assert recipe is not None
    assert (recipe.source, recipe.status, recipe.owner_id) == ("ai", "draft", user.id)
    assert recipe.embedding is not None
    assert seeded_db.scalar(select(Ingredient).where(Ingredient.name == "עירית")) is not None

    # The owner can see the draft; it is listed under "my recipes" but not in the catalog.
    detail = client.get(f"/api/recipes/{slug}").json()
    assert detail["source"] == "ai"
    assert detail["image_url"] is None
    assert [r["slug"] for r in client.get("/api/me/recipes").json()] == [slug]
    client.post("/api/auth/logout")
    assert client.get(f"/api/recipes/{slug}").status_code == 404


def test_save_unknown_generated_id(client: TestClient, seeded_db: Session) -> None:
    login_as(client, seeded_db)
    assert client.post("/api/generate/foo/save").status_code == 404


def test_generation_calls_are_logged(
    client: TestClient, llm: MockLLMClient, seeded_db: Session
) -> None:
    llm.responses = [recipe_json(steps=[]), recipe_json()]
    generate(client, {"mode": "free_text", "text": "foo"})
    calls = seeded_db.scalars(select(AICall)).all()
    assert [c.feature for c in calls] == ["generate", "generate"]
