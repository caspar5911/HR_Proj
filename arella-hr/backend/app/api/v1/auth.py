"""Authentication endpoints."""

from typing import Any

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.audit import record_audit
from app.middleware.auth import (
    get_current_user,
    create_access_token,
    create_refresh_token,
    verify_token_payload,
)
from app.middleware.rate_limit import limit_login, limit_refresh
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
    UserOut,
)
from app.services.token_revocation import REVOKED_REFRESH_TOKENS
from app.models.user import User

router = APIRouter()


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(limit_login)])
async def login(
    credentials: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Authenticate user by email + password, return JWT tokens.

    Every attempt is written to the audit trail (``auth.login.success`` /
    ``auth.login.failure``) so brute-force and account-takeover activity can
    be detected. Failure entries record the cause internally, but the HTTP
    response stays a generic 401 "Invalid credentials" for both an unknown
    email and a wrong password, so the API never confirms whether an address
    exists (user-enumeration defence).
    """
    stmt = select(User).where(User.email.ilike(credentials.email))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        await record_audit(
            db,
            user=None,
            request=request,
            action="auth.login.failure",
            entity="auth",
            changes={"email": credentials.email, "reason": "unknown_user"},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not _verify_password(credentials.password, user.hashed_password):
        await record_audit(
            db,
            user=user,
            request=request,
            action="auth.login.failure",
            entity="auth",
            changes={"reason": "invalid_credentials"},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        await record_audit(
            db,
            user=user,
            request=request,
            action="auth.login.failure",
            entity="auth",
            changes={"reason": "deactivated"},
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    subject = {"sub": str(user.id), "role": user.role, "ver": user.token_version}
    access_token = create_access_token(subject)
    refresh_token = create_refresh_token(subject)

    await record_audit(
        db,
        user=user,
        request=request,
        action="auth.login.success",
        entity="auth",
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token, token_type="bearer")


@router.post("/refresh", response_model=TokenResponse, dependencies=[Depends(limit_refresh)])
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> Any:
    """Exchange a refresh token for a new access token pair.

    Rotation: the presented token is revoked the moment it is used, so a
    captured refresh token can be replayed at most once.

    The token arrives in the JSON body (not the query string) so refresh JWTs
    don't get captured in access logs / proxy history.
    """
    payload = verify_token_payload(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    jti = payload.get("jti")
    if REVOKED_REFRESH_TOKENS.is_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    subject = payload.get("data") or {}
    if not subject.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    user_stmt = select(User).where(User.id == int(subject["sub"]))
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    # The token must have been minted under the user's current credential
    # version. A password change bumps the version, so any refresh token
    # issued before it is refused here instead of being extended.
    if int(subject.get("ver", 0)) != (user.token_version or 0):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please sign in again.",
        )

    # Rotate: invalidate the presented token before handing out its successor.
    REVOKED_REFRESH_TOKENS.revoke(jti, payload.get("exp", 0))

    new_subject = {"sub": str(user.id), "role": user.role, "ver": user.token_version}
    new_access = create_access_token(new_subject)
    new_refresh = create_refresh_token(new_subject)
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
async def logout(
    request: Request,
    body: LogoutRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Acknowledge logout and, when offered, revoke the caller's refresh token.

    JWTs are stateless, so a plain ``POST /logout`` (no body) still just
    acknowledges. When the client sends its refresh token, the server revokes
    it immediately so it cannot be replayed after logout. The endpoint stays
    unauthenticated on purpose: revoking a token you are handed is safe, and
    it keeps the call working even once the access token has expired.

    A successful revocation is recorded to the audit trail (``auth.logout``)
    so sign-out activity is as visible as sign-in.
    """
    if body and body.refresh_token:
        payload = verify_token_payload(body.refresh_token)
        if payload and payload.get("type") == "refresh":
            jti = payload.get("jti")
            REVOKED_REFRESH_TOKENS.revoke(jti, payload.get("exp", 0))
            sub = (payload.get("data") or {}).get("sub")
            if sub:
                user = (
                    await db.execute(select(User).where(User.id == int(sub)))
                ).scalar_one_or_none()
                await record_audit(
                    db,
                    user=user,
                    request=request,
                    action="auth.logout",
                    entity="auth",
                )
    return {"message": "Logged out successfully"}


# Minimum length for a new password. The current password is accepted as-is
# (legacy short passwords still verify); only *new* passwords are gated.
MIN_PASSWORD_LENGTH = 8


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Change the caller's own password.

    Requires the current password as a second factor so a stolen access token
    alone cannot reset the account. The new password must meet the minimum
    length. A successful change is written to the audit trail
    (``auth.password.change``) so credential rotation is visible to operators.
    """
    if not _verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    if len(body.new_password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"New password must be at least {MIN_PASSWORD_LENGTH} characters",
        )

    current_user.hashed_password = _hash_password(body.new_password)
    # Bump the credential version so every access and refresh token minted
    # before this change is rejected on its next use — a password rotation
    # must end every older session, not just the caller's.
    current_user.token_version = (current_user.token_version or 0) + 1
    await db.commit()

    await record_audit(
        db,
        user=current_user,
        request=request,
        action="auth.password.change",
        entity="auth",
    )

    return {"message": "Password updated successfully"}


# ── helpers ──────────────────────────────────────────────────────────────────

def _verify_password(plain: str, hashed: str) -> bool:
    """Verify plain-text password against bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _hash_password(plain: str) -> str:
    """Return a bcrypt hash of a plain-text password."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")