"""FastAPI application factory."""

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    admin,
    auth,
    favorites,
    health,
    placeholders,
    recipes,
    shopping,
    system,
)
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Smart Recipes API",
        version="0.1.0",
        description="API לאתר המתכונים החכם",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api = APIRouter(prefix="/api")
    for router in (
        health.router,
        auth.router,
        recipes.router,
        favorites.router,
        shopping.router,
        admin.router,
        system.router,
        *placeholders.routers,
    ):
        api.include_router(router)
    app.include_router(api)

    settings.media_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")
    return app


app = create_app()
