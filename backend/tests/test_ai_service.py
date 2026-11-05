from types import SimpleNamespace
from typing import Any

import httpx
import openai
import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models import AiFeature, AiUsageLog
from app.schemas.ai import FridgeMatch, FridgeSearchResult
from app.services.ai_service import AiRefusalError, AiService, AiUnavailableError

from .conftest import make_recipe


def status_error(code: int) -> openai.APIStatusError:
    request = httpx.Request("POST", "http://localhost")
    response = httpx.Response(code, request=request)
    cls = openai.RateLimitError if code == 429 else openai.APIStatusError
    return cls("boom", response=response, body=None)  # type: ignore[arg-type]


class FakeClient:
    def __init__(self, *outcomes: Any) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0
        self.responses = SimpleNamespace(parse=self._parse)

    def _parse(self, **_kwargs: Any) -> Any:
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def reply(parsed: Any) -> Any:
    return SimpleNamespace(
        output_parsed=parsed, id="resp_foo", usage=SimpleNamespace(input_tokens=11, output_tokens=7)
    )


def test_fridge_search_logs_usage_and_drops_unknown_ids(db: Session) -> None:
    recipe = make_recipe(db)
    parsed = FridgeSearchResult(
        matches=[
            FridgeMatch(recipe_id="unknown", match_score=99, missing_ingredients=[]),
            FridgeMatch(recipe_id=str(recipe.id), match_score=50, missing_ingredients=["baz"]),
        ]
    )
    service = AiService(FakeClient(reply(parsed)), "model-foo")  # type: ignore[arg-type]
    matches = service.fridge_search(db, ["bar"], [recipe])
    assert [m.recipe_id for m in matches] == [str(recipe.id)]
    log = db.query(AiUsageLog).one()
    assert (log.feature.value, log.model, log.input_tokens, log.output_tokens, log.response_id) == (
        "fridge_search", "model-foo", 11, 7, "resp_foo",
    )  # fmt: skip


@pytest.mark.parametrize("code", [429, 503])
def test_retries_once_on_429_and_5xx(db: Session, code: int) -> None:
    recipe = make_recipe(db)
    ok = reply(FridgeSearchResult(matches=[]))
    client = FakeClient(status_error(code), ok)
    AiService(client, "m").fridge_search(db, ["bar"], [recipe])  # type: ignore[arg-type]
    assert client.calls == 2


def test_gives_up_after_one_retry(db: Session) -> None:
    recipe = make_recipe(db)
    client = FakeClient(status_error(429), status_error(429))
    with pytest.raises(AiUnavailableError):
        AiService(client, "m").fridge_search(db, ["bar"], [recipe])  # type: ignore[arg-type]
    assert client.calls == 2
    assert db.query(AiUsageLog).count() == 0


def test_no_retry_on_client_errors(db: Session) -> None:
    recipe = make_recipe(db)
    client = FakeClient(status_error(400))
    with pytest.raises(AiUnavailableError):
        AiService(client, "m").fridge_search(db, ["bar"], [recipe])  # type: ignore[arg-type]
    assert client.calls == 1


def test_missing_api_key_is_unavailable(db: Session) -> None:
    recipe = make_recipe(db)
    with pytest.raises(AiUnavailableError):
        AiService(None, "m").estimate_nutrition(db, recipe)


def refusal_reply(text: str) -> Any:
    part = SimpleNamespace(type="refusal", refusal=text)
    message = SimpleNamespace(type="message", content=[part])
    return SimpleNamespace(
        output_parsed=None,
        output=[message],
        id="resp_bar",
        usage=SimpleNamespace(input_tokens=5, output_tokens=2),
    )


def test_refusal_raises_clear_error_and_logs_usage(db: Session) -> None:
    recipe = make_recipe(db)
    client = FakeClient(refusal_reply("lorem ipsum"))
    with pytest.raises(AiRefusalError, match="lorem ipsum"):
        AiService(client, "m").estimate_nutrition(db, recipe)  # type: ignore[arg-type]
    assert client.calls == 1
    assert db.query(AiUsageLog).count() == 1


def test_invalid_json_is_unavailable_without_retry(db: Session) -> None:
    recipe = make_recipe(db)
    try:
        FridgeSearchResult.model_validate_json("{not json")
    except ValidationError as exc:
        invalid = exc
    client = FakeClient(invalid)
    with pytest.raises(AiUnavailableError, match="invalid structured output"):
        AiService(client, "m").fridge_search(db, ["bar"], [recipe])  # type: ignore[arg-type]
    assert client.calls == 1
    assert db.query(AiUsageLog).count() == 0


def test_empty_output_without_refusal_is_unavailable(db: Session) -> None:
    recipe = make_recipe(db)
    client = FakeClient(reply(None))
    with pytest.raises(AiUnavailableError, match="empty structured output"):
        AiService(client, "m").estimate_nutrition(db, recipe)  # type: ignore[arg-type]


# ---- chat streaming -----------------------------------------------------------------------
def ev(type_: str, **kw: Any) -> Any:
    return SimpleNamespace(type=type_, **kw)


def completed(output: list[Any], rid: str) -> Any:
    usage = SimpleNamespace(input_tokens=1, output_tokens=1)
    return ev("response.completed", response=SimpleNamespace(id=rid, output=output, usage=usage))


class ChatClient:
    def __init__(self, *streams: Any) -> None:
        self.streams = list(streams)
        self.kwargs: list[dict[str, Any]] = []
        self.responses = SimpleNamespace(create=self._create)

    def _create(self, **kwargs: Any) -> Any:
        self.kwargs.append(kwargs)
        s = self.streams.pop(0)
        if isinstance(s, Exception):
            raise s
        return s


def call(name: str, args: str, cid: str = "call_foo") -> Any:
    return SimpleNamespace(type="function_call", name=name, arguments=args, call_id=cid)


def test_chat_stream_text_only(db: Session) -> None:
    recipe = make_recipe(db)
    client = ChatClient([ev("response.output_text.delta", delta="Lo"), completed([], "r1")])
    events = list(AiService(client, "m").chat_stream(db, recipe, "foo", None))  # type: ignore[arg-type]
    assert [e["event"] for e in events] == ["text_delta", "done"]
    assert events[-1]["data"] == {"response_id": "r1"}
    assert db.query(AiUsageLog).count() == 1


def test_chat_stream_scale_tool_loop(db: Session) -> None:
    recipe = make_recipe(db)  # 4 servings, bar 2 g
    client = ChatClient(
        [completed([call("scale_servings", '{"servings": 8}')], "r1")],
        [ev("response.output_text.delta", delta="ok"), completed([], "r2")],
    )
    events = list(AiService(client, "m").chat_stream(db, recipe, "foo", "r0"))  # type: ignore[arg-type]
    names = [e["event"] for e in events]
    assert names == ["tool_started", "recipe_scaled", "text_delta", "done"]
    assert events[1]["data"]["ingredients"][0]["quantity"] == 4.0
    assert client.kwargs[0]["previous_response_id"] == "r0"
    assert client.kwargs[1]["previous_response_id"] == "r1"
    assert client.kwargs[1]["input"][0]["call_id"] == "call_foo"


def test_chat_stream_tool_rounds_are_limited(db: Session) -> None:
    recipe = make_recipe(db)
    loop = [completed([call("scale_servings", '{"servings": 2}')], f"r{i}") for i in range(4)]
    client = ChatClient(*([x] for x in loop))
    events = list(AiService(client, "m").chat_stream(db, recipe, "foo", None))  # type: ignore[arg-type]
    assert len(client.kwargs) == 4  # 1 + MAX_TOOL_ROUNDS
    assert events[-1]["event"] == "done"


def test_chat_stream_adapt_tool(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.schemas.ai import AdaptedRecipe

    recipe = make_recipe(db)
    adapted = AdaptedRecipe(
        title="foo", description="", servings=2, prep_minutes=5, difficulty=recipe.difficulty,
        equipment=[], kashrut=recipe.kashrut, ingredients=[], steps=["baz"],
        changes_summary=["bar"], feasible=True, reason=None,
    )  # fmt: skip
    client = ChatClient(
        [completed([call("adapt_recipe", '{"instruction": "foo"}')], "r1")],
        [completed([], "r2")],
    )
    service = AiService(client, "m")  # type: ignore[arg-type]
    monkeypatch.setattr(service, "adapt_recipe", lambda *_a: adapted)
    events = list(service.chat_stream(db, recipe, "foo", None))
    assert [e["event"] for e in events] == ["tool_started", "recipe_adapted", "done"]


def test_chat_stream_bad_tool_arguments_do_not_crash(db: Session) -> None:
    recipe = make_recipe(db)
    client = ChatClient(
        [completed([call("scale_servings", "not json"), call("nope", "{}", "c2")], "r1")],
        [completed([], "r2")],
    )
    events = list(AiService(client, "m").chat_stream(db, recipe, "foo", None))  # type: ignore[arg-type]
    assert events[-1]["event"] == "done"


def test_chat_stream_errors(db: Session) -> None:
    recipe = make_recipe(db)
    no_key = list(AiService(None, "m").chat_stream(db, recipe, "foo", None))
    assert no_key == [{"event": "error", "data": {"code": "ai_unavailable"}}]
    boom = ChatClient(status_error(500))
    events = list(AiService(boom, "m").chat_stream(db, recipe, "foo", None))  # type: ignore[arg-type]
    assert events[0]["event"] == "error"
    failed = ChatClient([ev("response.failed")])
    events = list(AiService(failed, "m").chat_stream(db, recipe, "foo", None))  # type: ignore[arg-type]
    assert events[0]["event"] == "error"
    empty = ChatClient([])
    events = list(AiService(empty, "m").chat_stream(db, recipe, "foo", None))  # type: ignore[arg-type]
    assert events[0]["event"] == "error"


def test_timeout_is_a_single_attempt_and_maps_to_unavailable(db: Session) -> None:
    from app.config import Settings

    service = AiService.from_settings(Settings(openai_api_key="sk-foo"))
    assert service._client is not None
    assert service._client.max_retries == 0
    assert service._client.timeout == 30.0
    req = httpx.Request("POST", "http://x")
    client = FakeClient(openai.APITimeoutError(request=req))  # type: ignore[arg-type]
    with pytest.raises(AiUnavailableError):
        AiService(client, "m").parse(db, AiFeature.NUTRITION, "i", "p", FridgeSearchResult)  # type: ignore[arg-type]
