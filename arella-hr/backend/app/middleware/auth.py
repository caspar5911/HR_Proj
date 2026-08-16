"""JWT authentication middleware and utilities."""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User

# ---------------------------------------------------------------------------
# OAuth2 bearer scheme (enables Swagger UI "Authorize" button)
# ---------------------------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ── token creation ───────────────────────────────────────────────────────────

def create_access_token(subject: dict, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token (default expiry: 15 minutes)."""
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {"exp": expire, "iat": datetime.now(timezone.utc), "data": subject}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: dict, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT refresh token (default expiry: 7 days).

    Carries a unique ``jti`` so individual tokens can be revoked later
    (logout / rotation) — see ``app.services.token_revocation``.
    """
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
    now = datetime.now(timezone.utc)
    payload = {
        "exp": expire,
        "iat": now,
        "data": subject,
        "type": "refresh",
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


# ── token verification ───────────────────────────────────────────────────────

def verify_token_payload(token: str) -> dict | None:
    """Decode and verify a JWT. Returns the full payload dict or None."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None


def verify_token(token: str) -> dict | None:
    """Decode and verify a JWT. Returns the inner ``data`` dict or None.

    The payload is shaped ``{"exp", "iat", "data": {...}}`` (with ``"type"``
    added for refresh tokens); callers that need the top-level claims should
    use :func:`verify_token_payload` instead.
    """
    payload = verify_token_payload(token)
    if payload is None:
        return None
    return payload.get("data")


# ── dependency injectors ─────────────────────────────────────────────────────

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency: resolve the current user from a Bearer token.

    Raises 401 if the token is invalid or the user is not found.
    Raises 403 if the account is deactivated.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = verify_token(token)
    if not payload:
        raise credentials_exception

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception

    stmt = select(User).where(User.id == int(user_id))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    return user


def require_role(*allowed_roles: str):
    """Return a FastAPI dependency that enforces one or more roles.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role("admin"))])
        async def admin_endpoint(): ...
    """
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return _check