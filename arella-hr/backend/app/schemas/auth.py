"""Pydantic schemas for authentication."""

from datetime import datetime
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LogoutRequest(BaseModel):
    """Optional logout payload.

    Carrying the refresh token lets the server revoke it immediately so it
    cannot be replayed after logout. Omitting it (or sending no body at all)
    keeps the old stateless logout behaviour — the endpoint stays a simple
    acknowledgement.
    """

    refresh_token: str | None = None


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}