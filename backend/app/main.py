"""FastAPI application factory."""

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    admin_images,
    admin_recipes,
    assistant,
    auth,
    favorites,
    generate,
    health,
    ingredients,
    me,
    recipes,
    recommendations,
    search,
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
    routers = (
        health,
        auth,
        me,
        recommendations,  # before recipes: /recipes/{id}/similar
        recipes,
        ingredients,
        search,
        assistant,
        generate,
        favorites,
        shopping,
        admin_recipes,
        admin_images,
        system,
    )
    for module in routers:
        api.include_router(module.router)
    app.include_router(api)

    settings.media_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")
    return app


app = create_app()
