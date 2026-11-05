from types import SimpleNamespace
from typing import Any

import httpx
import openai
import pytest
from sqlalchemy.orm import Session

from app.models import AiUsageLog
from app.schemas.ai import FridgeMatch, FridgeSearchResult
from app.services.ai_service import AiService, AiUnavailableError

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
