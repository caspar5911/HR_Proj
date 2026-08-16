"""FastAPI application factory.

On startup the backend applies any pending Alembic migrations itself, so
``docker compose up`` is all that is needed — no separate
``alembic upgrade head`` step.
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Add the backend directory to sys.path so `app.*` imports work from any cwd
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.utils.errors import register_exception_handlers

logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("arella.startup")

# The backend directory (repo/backend/) — where alembic.ini lives
BACKEND_DIR = Path(__file__).resolve().parent.parent

# How long to keep retrying while the database container is still coming up
MIGRATION_RETRIES = 15
MIGRATION_RETRY_DELAY_S = 2.0

# Out-of-the-box secrets shipped in the defaults. The one-action local stack
# relies on these, so their presence is a *warning*, never a hard failure.
# (SECRET_KEY is not checked here: app.config refuses to start with the old
# well-known default, so a weak signing key is a hard failure, not a warning.)
_DEFAULT_ADMIN_PASSWORD = "admin123"


def _warn_on_default_secrets() -> None:
    """Log a prominent warning for every well-known secret still in use.

    A default superadmin password is a standing open backdoor. Production
    deployments must override it via the SEED_ADMIN_PASSWORD env var.
    """
    if settings.SEED_ADMIN_PASSWORD == _DEFAULT_ADMIN_PASSWORD:
        logger.warning(
            "SECURITY: SEED_ADMIN_PASSWORD is still the built-in default "
            "(admin123) — set SEED_ADMIN_PASSWORD before deploying."
        )


def _upgrade_to_head() -> None:
    """Run ``alembic upgrade head`` synchronously.

    Alembic's async env.py calls ``asyncio.run()``, which is not allowed from
    inside a running event loop — so this must execute in a worker thread
    (see ``asyncio.to_thread`` below).
    """
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    command.upgrade(cfg, "head")


async def _run_migrations() -> None:
    """Apply pending migrations, retrying while the database is still booting."""
    # Tests use an in-memory SQLite schema built from Base.metadata — skip.
    if settings.DATABASE_URL.startswith("sqlite"):
        return
    for attempt in range(1, MIGRATION_RETRIES + 1):
        try:
            await asyncio.to_thread(_upgrade_to_head)
            logger.info("Database schema is up to date (alembic upgrade head).")
            return
        except Exception as exc:  # noqa: BLE001 — retry on any startup failure
            if attempt == MIGRATION_RETRIES:
                raise
            logger.warning(
                "Migrations not ready yet (attempt %d/%d): %s — retrying in %.0fs",
                attempt, MIGRATION_RETRIES, exc, MIGRATION_RETRY_DELAY_S,
            )
            await asyncio.sleep(MIGRATION_RETRY_DELAY_S)


async def _seed_admin() -> None:
    """Create the initial superadmin if it does not already exist.

    Reuses the shared ``seed`` helper from ``scripts/seed.py`` — the same
    logic ``python -m scripts.seed`` runs, so the two paths never drift.
    Password is intentionally not logged; see the SEED_ADMIN_PASSWORD env var.
    """
    from app.database import async_session
    from scripts.seed import seed

    async with async_session() as db:
        await seed(db)
    logger.info("Admin user ensured: %s", settings.SEED_ADMIN_EMAIL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: migrations + seed admin before accepting requests."""
    _warn_on_default_secrets()
    await _run_migrations()
    await _seed_admin()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="HR Management System for SMBs",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # Structured error responses — every error carries a machine-readable code.
    register_exception_handlers(app)

    # CORS — allow configured origins (dev frontend, GitHub Pages, …)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Defensive security headers on every response. Added last so it sits
    # outermost and also covers CORS preflight responses.
    app.add_middleware(SecurityHeadersMiddleware)

    # Health check
    @app.get("/health")
    async def healthcheck() -> dict:
        return {"status": "ok", "app": settings.APP_NAME}

    # Versioned API
    from app.api.v1 import router as api_v1_router
    app.include_router(api_v1_router, prefix="/api/v1")

    return app


app = create_app()
