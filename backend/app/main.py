"""FastAPI application factory."""

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import admin, ai, health, recipes
from app.config import get_settings
from app.services import storage
from app.services.ai_service import AiUnavailableError


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Smart Recipes API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Total-Count"],
    )

    @app.exception_handler(AiUnavailableError)
    async def _ai_unavailable(_request: Request, _exc: AiUnavailableError) -> JSONResponse:
        # The client maps this code to a friendly message in the UI language.
        return JSONResponse({"detail": "ai_unavailable"}, status_code=503)

    api = APIRouter(prefix="/api")
    for router in (health.router, recipes.router, ai.router, admin.router):
        api.include_router(router)
    app.include_router(api)

    # Only approved images live in public/; pending ones are never served.
    app.mount("/media", StaticFiles(directory=storage.public_dir()), name="media")
    return app


app = create_app()
