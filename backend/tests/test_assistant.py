import json

from fastapi.testclient import TestClient

from app.services.ai.client import MockLLMClient
from app.services.ai.prompts import FILTERS_MARKER
from tests.conftest import parse_sse

FILTERS: dict[str, object] = {
    "kosher_type": None,
    "dish_type": "main",
    "difficulty": None,
    "max_minutes": None,
    "include_ingredients": [],
    "exclude_ingredients": [],
    "diet_tags": [],
    "text": None,
}


def _chat(client: TestClient, text: str = "מה לבשל לארוחת ערב?") -> list[tuple[str, object]]:
    res = client.post("/api/assistant/chat", json={"messages": [{"role": "user", "content": text}]})
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/event-stream")
    return parse_sse(res.text)


def test_chat_streams_text_and_returns_recipes(client: TestClient, llm: MockLLMClient) -> None:
    reply = "הנה כמה מנות עיקריות מהקטלוג שלנו שיתאימו לארוחת ערב."
    llm.responses = [f"{reply}\n{FILTERS_MARKER}{json.dumps(FILTERS)}"]
    events = _chat(client)

    text = "".join(d["text"] for e, d in events if e == "delta")  # type: ignore[index]
    assert text.strip() == reply
    assert FILTERS_MARKER not in text
    recipes = next(d for e, d in events if e == "recipes")
    assert isinstance(recipes, list)
    assert 1 <= len(recipes) <= 3
    assert all(r["dish_type"] == "main" for r in recipes)
    assert events[-1][0] == "done"


def test_chat_clarifying_question_has_no_recipes(client: TestClient, llm: MockLLMClient) -> None:
    llm.responses = [f"בשרי, חלבי או פרווה?\n{FILTERS_MARKER}null"]
    events = _chat(client, "משהו טעים")
    assert ("recipes", []) in events


def test_chat_ignores_malformed_filters(client: TestClient, llm: MockLLMClient) -> None:
    llm.responses = [f"foo\n{FILTERS_MARKER}{{not json"]
    assert ("recipes", []) in _chat(client)


def test_chat_reports_ai_error(client: TestClient) -> None:
    events = _chat(client)
    assert events[0][0] == "error"


def test_chat_validates_conversation(client: TestClient) -> None:
    bad = {"messages": [{"role": "assistant", "content": "foo"}]}
    assert client.post("/api/assistant/chat", json=bad).status_code == 422
    assert client.post("/api/assistant/chat", json={"messages": []}).status_code == 422
