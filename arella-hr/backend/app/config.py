"""Application settings — loaded from environment / .env file."""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "Arella HR System"
    DEBUG: bool = False

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/arellahr"

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


settings = Settings()