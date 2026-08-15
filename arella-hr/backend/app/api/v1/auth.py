"""Authentication endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import (
    get_current_user,
    create_access_token,
    create_refresh_token,
)
from app.middleware.rate_limit import limit_login, limit_refresh
from app.schemas.auth import LoginRequest, TokenResponse, UserOut
from app.models.user import User

router = APIRouter()


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(limit_login)])
async def login(credentials: LoginRequest, db: AsyncSession = Depends(get_db)) -> Any:
    """Authenticate user by email + password, return JWT tokens."""
    stmt = select(User).where(User.email.ilike(credentials.email))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not _verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id), "role": user.role})

    return TokenResponse(access_token=access_token, refresh_token=refresh_token, token_type="bearer")


@router.post("/refresh", response_model=TokenResponse, dependencies=[Depends(limit_refresh)])
async def refresh(refresh_token: str, db: AsyncSession = Depends(get_db)) -> Any:
    """Exchange a refresh token for a new access token pair."""
    from app.middleware.auth import verify_token_payload

    payload = verify_token_payload(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    subject = payload.get("data") or {}
    if not subject.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    user_stmt = select(User).where(User.id == int(subject["sub"]))
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    new_access = create_access_token({"sub": str(user.id), "role": user.role})
    new_refresh = create_refresh_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(access_token=new_access, refresh_token=new_refresh, token_type="bearer")


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> Any:
    """Return the currently authenticated user."""
    return UserOut(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )


@router.post("/logout")
async def logout() -> dict:
    """Client-side logout endpoint (stateless JWT — no server invalidation needed)."""
    return {"message": "Logged out successfully"}


# ── helpers ──────────────────────────────────────────────────────────────────

def _verify_password(plain: str, hashed: str) -> bool:
    """Verify plain-text password against bcrypt hash."""
    import bcrypt
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))