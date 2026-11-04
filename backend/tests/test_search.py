import json

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AICall
from app.services.ai.client import MockLLMClient

EMPTY: dict[str, object] = {
    "kosher_type": None,
    "dish_type": None,
    "difficulty": None,
    "max_minutes": None,
    "include_ingredients": [],
    "exclude_ingredients": [],
    "diet_tags": [],
    "text": None,
}


def test_suggest_recipes_ingredients_categories(client: TestClient) -> None:
    res = client.get("/api/search/suggest", params={"q": "קינואה"})
    assert res.status_code == 200
    types = {s["type"] for s in res.json()}
    assert types == {"recipe", "ingredient"}

    cats = client.get("/api/search/suggest", params={"q": "חלבי"}).json()
    assert cats[0] == {"type": "category", "label": "חלבי", "value": "kosher_type=dairy"}


def test_suggest_limit_and_prefix_first(client: TestClient) -> None:
    res = client.get("/api/search/suggest", params={"q": "ב"}).json()
    assert len(res) <= 8
    assert res[0]["label"].startswith("ב")


def test_suggest_requires_query(client: TestClient) -> None:
    assert client.get("/api/search/suggest", params={"q": ""}).status_code == 422


def test_smart_search_uses_ai_filters(
    client: TestClient, llm: MockLLMClient, seeded_db: Session
) -> None:
    llm.responses = [json.dumps({**EMPTY, "kosher_type": "dairy", "max_minutes": 30})]
    res = client.post("/api/search/smart", json={"query": "משהו חלבי בחצי שעה"})
    body = res.json()
    assert res.status_code == 200
    assert body["fallback"] is False
    assert body["filters"]["kosher_type"] == "dairy"
    assert [r["slug"] for r in body["results"]] == ["shakshuka-yeruka"]
    assert llm.calls[0]["schema"] is not None
    assert seeded_db.scalars(select(AICall)).one().feature == "search"


def test_smart_search_suggests_relaxation(client: TestClient, llm: MockLLMClient) -> None:
    llm.responses = [json.dumps({**EMPTY, "kosher_type": "meat", "max_minutes": 10})]
    body = client.post("/api/search/smart", json={"query": "בשרי בעשר דקות"}).json()
    assert body["total"] == 0
    assert body["relaxations"][0]["remove"] == "max_minutes"
    assert body["relaxations"][0]["message"] == "נמצאו 1 מתכונים בלי מגבלת הזמן"


def test_smart_search_include_exclude_ingredients(client: TestClient, llm: MockLLMClient) -> None:
    llm.responses = [
        json.dumps({**EMPTY, "include_ingredients": ["בצל"], "exclude_ingredients": ["ביצים"]})
    ]
    body = client.post("/api/search/smart", json={"query": "עם בצל בלי ביצים"}).json()
    assert [r["slug"] for r in body["results"]] == ["salat-kinoa"]


def test_smart_search_falls_back_when_ai_unavailable(client: TestClient) -> None:
    body = client.post("/api/search/smart", json={"query": "סלט קינואה טעים"}).json()
    assert body["fallback"] is True
    assert "salat-kinoa" in [r["slug"] for r in body["results"]]


def test_smart_search_falls_back_on_invalid_json(client: TestClient, llm: MockLLMClient) -> None:
    llm.responses = ["not json"]
    body = client.post("/api/search/smart", json={"query": "שקשוקה"}).json()
    assert body["fallback"] is True
    assert body["results"][0]["slug"] == "shakshuka-yeruka"


def test_ai_rate_limit(client: TestClient) -> None:
    codes = [client.post("/api/search/smart", json={"query": "foo"}).status_code for _ in range(11)]
    assert codes[:10] == [200] * 10
    assert codes[10] == 429
