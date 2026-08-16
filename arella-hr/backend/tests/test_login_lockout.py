"""Per-account brute-force defence.

The per-IP rate limit stops mass sweeps across many accounts, but a
sustained attack on a single account could continue from rotating IPs. So
the account itself locks: after MAX_LOGIN_ATTEMPTS consecutive failures,
logins are refused for LOGIN_LOCKOUT_MINUTES — even with the correct
password. A successful login clears the counter.

Unknown emails also pass through a dummy bcrypt check so response timing
never leaks which addresses exist (user-enumeration defence).

NOTE: each test must stay under 10 login attempts — the per-IP rate
limiter (10 / 5 min) is reset per test, not per assertion.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.api.v1.auth import MAX_LOGIN_ATTEMPTS
from app.models.user import User
from conftest import API, TEST_PASSWORD, auth_headers, login, seed_user

WRONG = "wrong-password-xyz"


async def _fail_login(client, email: str) -> None:
    resp = await client.post(f"{API}/auth/login", json={"email": email, "password": WRONG})
    assert resp.status_code == 401, resp.text


async def _lock_out(client, email: str) -> None:
    for _ in range(MAX_LOGIN_ATTEMPTS):
        await _fail_login(client, email)


async def test_lockout_refuses_even_correct_password(client, db):
    await seed_user(db, email="lock1@test.com")
    await _lock_out(client, "lock1@test.com")

    resp = await client.post(
        f"{API}/auth/login", json={"email": "lock1@test.com", "password": TEST_PASSWORD}
    )
    assert resp.status_code == 403, resp.text
    assert "locked" in resp.json()["detail"]["message"].lower()


async def test_lockout_is_audited(client, db):
    await seed_user(db, email="admin@test.com", role="admin")
    await seed_user(db, email="lock2@test.com")
    await _lock_out(client, "lock2@test.com")
    admin = await login(client, "admin@test.com")

    resp = await client.get(
        f"{API}/audit-logs/",
        params={"entity": "auth", "page_size": 200},
        headers=auth_headers(admin["access_token"]),
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    reasons = [
        i.get("changes", {}).get("reason")
        for i in items
        if i["action"] == "auth.login.failure"
    ]
    # Attempts 1-4 are plain failures; only the fifth one triggers the lock.
    assert "locked_out" in reasons
    assert reasons.count("locked_out") == 1
    assert reasons.count("invalid_credentials") == MAX_LOGIN_ATTEMPTS - 1


async def test_lockout_expiry_allows_login_again(client, db):
    await seed_user(db, email="lock3@test.com")
    await _lock_out(client, "lock3@test.com")

    user = (await db.execute(select(User).where(User.email == "lock3@test.com"))).scalar_one()
    assert user.locked_until is not None
    # Push the lock into the past — no need to wait the real window.
    user.locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)
    await db.commit()

    tokens = await login(client, "lock3@test.com")
    assert tokens["access_token"]


async def test_success_resets_failure_counter(client, db):
    await seed_user(db, email="lock4@test.com")
    for _ in range(MAX_LOGIN_ATTEMPTS - 1):
        await _fail_login(client, "lock4@test.com")
    await login(client, "lock4@test.com")  # clears the counter
    for _ in range(3):
        await _fail_login(client, "lock4@test.com")
    # Without the reset, 4 prior + 3 new failures would already be locked;
    # with it, only 3 are pending, so login still works.
    tokens = await login(client, "lock4@test.com")
    assert tokens["access_token"]


async def test_unknown_email_still_401(client, db):
    # The timing-equalisation path (dummy hash) must not crash and must
    # keep the generic 401 that hides whether the address exists.
    resp = await client.post(
        f"{API}/auth/login",
        json={"email": "nobody@example.org", "password": WRONG},
    )
    assert resp.status_code == 401, resp.text
