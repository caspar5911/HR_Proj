"""FastAPI application factory."""

import sys
from pathlib import Path

# Add the backend directory to sys.path so `app.*` imports work from any cwd
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.utils.errors import register_exception_handlers


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="HR Management System for SMBs",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    # Structured error responses — every error carries a machine-readable code.
    register_exception_handlers(app)

    # CORS — allow the dev frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check
    @app.get("/health")
    async def healthcheck() -> dict:
        return {"status": "ok", "app": settings.APP_NAME}

    # Versioned API
    from app.api.v1 import router as api_v1_router
    app.include_router(api_v1_router, prefix="/api/v1")

    return app


app = create_app()