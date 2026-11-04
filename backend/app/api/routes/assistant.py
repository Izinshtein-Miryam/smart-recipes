import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from app.api.serializers import SSE_HEADERS, sse, to_cards
from app.core.deps import LLM, AIRateLimited, DbSession, OptionalUser
from app.models import AIFeature
from app.schemas.ai import ChatIn
from app.schemas.search import FiltersModel
from app.services import catalog
from app.services.ai.client import ChatMessage, LLMError
from app.services.ai.prompts import ASSISTANT_SYSTEM, FILTERS_MARKER
from app.services.ai.service import AIService

router = APIRouter(prefix="/assistant", tags=["assistant"])

MAX_RECIPES = 3


def parse_filters(tail: str) -> FiltersModel | None:
    tail = tail.strip()
    if not tail or tail == "null":
        return None
    try:
        return FiltersModel.model_validate(json.loads(tail.splitlines()[0]))
    except (json.JSONDecodeError, ValidationError, IndexError):
        return None


@router.post(
    "/chat",
    summary="תור שיחה בצ'אט העוזר (SSE)",
    response_class=StreamingResponse,
    dependencies=[AIRateLimited],
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def chat(body: ChatIn, db: DbSession, user: OptionalUser, llm: LLM) -> StreamingResponse:
    """Events: `delta` {text} (repeated), `recipes` [cards], `done`; or `error` {message}."""
    messages: list[ChatMessage] = [{"role": m.role, "content": m.content} for m in body.messages]
    ai = AIService(llm, db, user.id if user else None)

    async def events() -> AsyncIterator[str]:
        buf, emitted = "", 0
        try:
            async for chunk in ai.stream(
                AIFeature.CHAT,
                system=ASSISTANT_SYSTEM,
                messages=messages,
                effort="low",
                max_tokens=4000,
            ):
                if not isinstance(chunk, str):
                    continue
                buf += chunk
                # Stream only the user-facing text; hold back anything that may be the marker.
                idx = buf.find(FILTERS_MARKER)
                safe = idx if idx >= 0 else len(buf) - len(FILTERS_MARKER)
                if safe > emitted:
                    yield sse("delta", {"text": buf[emitted:safe]})
                    emitted = safe
        except LLMError as e:
            yield sse("error", {"message": str(e)})
            return

        text, _, tail = buf.partition(FILTERS_MARKER)
        if len(text) > emitted:
            yield sse("delta", {"text": text[emitted:]})
        filters = parse_filters(tail)
        recipes = catalog.search(db, filters.to_filters(), limit=MAX_RECIPES) if filters else []
        yield sse("recipes", [c.model_dump(mode="json") for c in to_cards(recipes)])
        yield sse("done", {})

    return StreamingResponse(events(), media_type="text/event-stream", headers=SSE_HEADERS)
