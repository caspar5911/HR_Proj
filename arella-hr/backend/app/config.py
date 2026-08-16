"""Application settings — loaded from environment / .env file."""

import os

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings

# Used when neither DATABASE_URL nor the individual connection parts are set
# (i.e. a bare dev machine with no .env). Docker Compose and .env both provide
# a full DATABASE_URL, so this is only a last-resort fallback.
_DEV_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/arellahr"

# The JWT signing key that must never end up in a running deployment: it was
# the default shipped in this repo, so anyone who reads the code can forge
# valid tokens with it.
_INSECURE_SECRET_KEY = "change-me-in-production"
_MIN_SECRET_KEY_LENGTH = 32


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
    # No usable default on purpose — _check_secret_key rejects an empty,
    # short, or well-known value, so the process fails fast at startup.
    SECRET_KEY: str = ""
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

    # ── Rate limiting ───────────────────────────────────────────────────────
    # When the app sits behind a reverse proxy / load balancer that rewrites
    # X-Forwarded-For, set this to true so rate limits key on the *real*
    # client IP instead of the proxy's own address (which would be shared by
    # every visitor and cause mass 429s). Leave false when the proxy does NOT
    # append X-Forwarded-For, otherwise a client can spoof the header to
    # bypass the limit.
    TRUST_PROXY_HEADERS: bool = False

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

    @model_validator(mode="after")
    def _check_secret_key(self) -> "Settings":
        """Refuse to start with a missing or known-insecure JWT signing key.

        Every access and refresh token is signed with ``SECRET_KEY``; a
        deployment running on the bundled default (or an empty value) would
        let anyone mint valid tokens and impersonate any user. Failing fast
        at startup — with an actionable message — is far better than
        signing sessions with a publicly known key.
        """
        if (
            not self.SECRET_KEY
            or self.SECRET_KEY == _INSECURE_SECRET_KEY
            or len(self.SECRET_KEY) < _MIN_SECRET_KEY_LENGTH
        ):
            raise RuntimeError(
                "SECRET_KEY is missing or insecure. Set a random value of at "
                "least 32 characters — e.g. "
                "python -c \"import secrets; print(secrets.token_urlsafe(48))\" — "
                "and provide it to the process (or add SECRET_KEY=... to .env)."
            )
        return self


settings = Settings()
