"""Tests for the /auth endpoints: login, refresh, me, logout + rate limiting."""

from datetime import timedelta

from app.middleware.auth import create_access_token
from conftest import API, TEST_PASSWORD, auth_headers, login, seed_user


# ── login ───────────────────────────────────────────────────────────────────


async def test_login_success(client, db):
    await seed_user(db, email="user@test.com")
    resp = await client.post(
        f"{API}/auth/login", json={"email": "user@test.com", "password": TEST_PASSWORD}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


async def test_login_invalid_password(client, db):
    await seed_user(db, email="user@test.com")
    resp = await client.post(
        f"{API}/auth/login", json={"email": "user@test.com", "password": "wrong-password"}
    )
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "UNAUTHORIZED"


async def test_login_unknown_user(client, db):
    resp = await client.post(
        f"{API}/auth/login", json={"email": "ghost@test.com", "password": TEST_PASSWORD}
    )
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "UNAUTHORIZED"


async def test_login_deactivated_account(client, db):
    await seed_user(db, email="off@test.com", is_active=False)
    resp = await client.post(
        f"{API}/auth/login", json={"email": "off@test.com", "password": TEST_PASSWORD}
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "FORBIDDEN"


async def test_login_missing_field_is_validation_error(client, db):
    resp = await client.post(f"{API}/auth/login", json={"email": "user@test.com"})
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "VALIDATION_ERROR"


# ── refresh ─────────────────────────────────────────────────────────────────


# NOTE: the refresh token travels in the JSON body, never the query string —
# a refresh JWT in the URL would land in access logs / proxy history. These
# tests therefore post ``json={"refresh_token": ...}``.


async def test_refresh_returns_new_token_pair(client, db):
    await seed_user(db, email="user@test.com")
    tokens = await login(client, "user@test.com")
    resp = await client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


async def test_refresh_rejects_access_token(client, db):
    await seed_user(db, email="user@test.com")
    tokens = await login(client, "user@test.com")
    resp = await client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "UNAUTHORIZED"


async def test_refresh_rejects_garbage_token(client, db):
    await seed_user(db, email="user@test.com")
    resp = await client.post(f"{API}/auth/refresh", json={"refresh_token": "not-a-jwt"})
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "UNAUTHORIZED"


# ── revocation & rotation ───────────────────────────────────────────────────


async def test_refresh_token_is_single_use(client, db):
    """A refresh token is revoked the moment it is used (rotation)."""
    await seed_user(db, email="user@test.com")
    tokens = await login(client, "user@test.com")
    original = tokens["refresh_token"]

    # First use rotates to a fresh pair.
    resp = await client.post(f"{API}/auth/refresh", json={"refresh_token": original})
    assert resp.status_code == 200
    rotated = resp.json()["refresh_token"]
    assert rotated != original

    # Replaying the original must now fail.
    resp = await client.post(f"{API}/auth/refresh", json={"refresh_token": original})
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "UNAUTHORIZED"

    # The rotated successor still works.
    resp = await client.post(f"{API}/auth/refresh", json={"refresh_token": rotated})
    assert resp.status_code == 200


async def test_logout_revokes_presented_refresh_token(client, db):
    """Logout carrying the refresh token revokes it immediately."""
    await seed_user(db, email="user@test.com")
    tokens = await login(client, "user@test.com")

    resp = await client.post(
        f"{API}/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert resp.status_code == 200

    # The revoked token can no longer be refreshed.
    resp = await client.post(
        f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "UNAUTHORIZED"


async def test_logout_empty_body_still_acknowledges(client, db):
    """A body-less logout (old behaviour) still gets a 200 acknowledgement."""
    resp = await client.post(f"{API}/auth/logout", json={})
    assert resp.status_code == 200
    assert "message" in resp.json()


# ── me ──────────────────────────────────────────────────────────────────────


async def test_me_returns_current_user(client, db):
    await seed_user(db, email="me@test.com", role="manager")
    token = (await login(client, "me@test.com"))["access_token"]
    resp = await client.get(f"{API}/auth/me", headers=auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "me@test.com"
    assert body["role"] == "manager"


async def test_me_requires_authentication(client, db):
    resp = await client.get(f"{API}/auth/me")
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "UNAUTHORIZED"


async def test_me_rejects_expired_token(client, db):
    user = await seed_user(db, email="me@test.com")
    token = create_access_token(
        {"sub": str(user.id), "role": user.role}, expires_delta=timedelta(seconds=-10)
    )
    resp = await client.get(f"{API}/auth/me", headers=auth_headers(token))
    assert resp.status_code == 401


# ── logout ──────────────────────────────────────────────────────────────────


async def test_logout_acknowledges(client, db):
    resp = await client.post(f"{API}/auth/logout")
    assert resp.status_code == 200
    assert "message" in resp.json()


# ── rate limiting ───────────────────────────────────────────────────────────


async def test_login_rate_limit_blocks_after_10_attempts(client, db):
    await seed_user(db, email="user@test.com")
    payload = {"email": "user@test.com", "password": TEST_PASSWORD}
    for _ in range(10):
        resp = await client.post(f"{API}/auth/login", json=payload)
        assert resp.status_code == 200
    resp = await client.post(f"{API}/auth/login", json=payload)
    assert resp.status_code == 429
    assert resp.json()["detail"]["code"] == "RATE_LIMITED"


async def test_refresh_rate_limit_blocks_after_20_attempts(client, db):
    await seed_user(db, email="user@test.com")
    tokens = await login(client, "user@test.com")
    # Rotate the token on each call — refresh is now single-use, so the same
    # token would be revoked after its first use.
    for _ in range(20):
        resp = await client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert resp.status_code == 200, resp.text
        tokens["refresh_token"] = resp.json()["refresh_token"]
    resp = await client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 429
    assert resp.json()["detail"]["code"] == "RATE_LIMITED"
