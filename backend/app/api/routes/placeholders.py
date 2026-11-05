"""Routers for endpoints defined in the spec but not implemented yet.

Each endpoint is registered (so it appears in /docs) and returns 501 until implemented.
Move an endpoint to its own module when you start working on it.
"""

from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser


def _todo() -> None:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Not implemented yet")


search = APIRouter(prefix="/search", tags=["search"])
assistant = APIRouter(prefix="/assistant", tags=["assistant"])
generate = APIRouter(prefix="/generate", tags=["generate"])
recommendations = APIRouter(tags=["recommendations"])


@search.get("/suggest", summary="השלמה אוטומטית (מקומי, ללא AI)")
def suggest(q: str) -> None:
    _todo()


@search.post("/smart", summary="חיפוש בשפה חופשית")
def smart_search() -> None:
    _todo()


@assistant.post("/chat", summary="תור שיחה בצ'אט העוזר (SSE)")
def chat() -> None:
    _todo()


@generate.post("", summary="יצירה חכמה (SSE)")
def generate_recipe() -> None:
    _todo()


@generate.post("/{recipe_id}/save", summary="שמירת מתכון שנוצר")
def save_generated(recipe_id: int, user: CurrentUser) -> None:
    _todo()


@recommendations.get("/recommendations/home", summary="מובחר + 4 לפי הקשר זמן")
def home_recommendations() -> None:
    _todo()


@recommendations.get("/recipes/{recipe_id}/similar", summary="מתכונים דומים")
def similar(recipe_id: int) -> None:
    _todo()


routers = [search, assistant, generate, recommendations]
