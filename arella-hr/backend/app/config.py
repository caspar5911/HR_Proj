"""Application settings — loaded from environment / .env file."""

import os

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings

# Used when neither DATABASE_URL nor the individual connection parts are set
# (i.e. a bare dev machine with no .env). Docker Compose and .env both provide
# a full DATABASE_URL, so this is only a last-resort fallback.
_DEV_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/arellahr"


def _to_asyncpg(url: str) -> str:
    """Return *url* using the SQLAlchemy asyncpg dialect.

    Some platforms (e.g. Railway's Postgres plugin) hand out a plain
    ``postgres://`` / ``postgresql://`` connection string, which asyncpg's
    SQLAlchemy dialect does not understand. Rewrite the scheme in that case.
    """
    for plain in ("postgresql://", "postgres://"):
        if url.startswith(plain):
            return "postgresql+asyncpg://" + url[len(plain):]
    return url


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "Arella HR System"
    DEBUG: bool = False

    # ── Database ─────────────────────────────────────────────────────────────
    # Either a full URL (dev / Docker / .env) OR left unset when a PaaS such
    # as Railway injects the individual parts below — resolved in
    # _resolve_database_url. Always a fully-formed asyncpg URL after init.
    DATABASE_URL: str | None = None

    # ── Auth ─────────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production"
    # Accepts both ALGORITHM (legacy) and JWT_ALGORITHM
    JWT_ALGORITHM: str = Field(default="HS256", alias="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Email ────────────────────────────────────────────────────────────────
    # Console-mocked transport for now; toggle off to suppress all notifications.
    EMAIL_ENABLED: bool = True

    # ── CORS ───────────────────────────────────────────────────────────────
    # Comma-separated list of browser origins allowed to call the API
    # (the dev frontend, a GitHub Pages deployment, …). Same-origin
    # deployments (nginx proxy) need no entry.
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ── Seed (dev convenience) ───────────────────────────────────────────────
    SEED_ADMIN_EMAIL: str = "admin@example.com"
    SEED_ADMIN_PASSWORD: str = "admin123"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @model_validator(mode="after")
    def _resolve_database_url(self) -> "Settings":
        """Guarantee DATABASE_URL is a usable asyncpg connection string.

        1. If a full URL was provided, normalise its scheme to asyncpg.
        2. Otherwise assemble it from the individual parts PaaS providers
           inject when a database is linked (``HOST``/``DB_HOST`` etc.).
        3. Fall back to the local dev default.
        """
        if self.DATABASE_URL:
            self.DATABASE_URL = _to_asyncpg(self.DATABASE_URL)
            return self

        host = os.environ.get("DB_HOST") or os.environ.get("HOST")
        user = os.environ.get("DB_USER") or os.environ.get("USER")
        if host and user:
            port = os.environ.get("DB_PORT") or os.environ.get("PORT") or "5432"
            password = os.environ.get("DB_PASSWORD") or os.environ.get("PASSWORD") or ""
            name = (
                os.environ.get("DB_NAME")
                or os.environ.get("DB_DATABASE")
                or os.environ.get("DATABASE")
                or "arellahr"
            )
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"
            )
        else:
            self.DATABASE_URL = _DEV_DATABASE_URL
        return self


settings = Settings()
