"""Authentication events must land in the audit trail.

Login (success *and* failure) and logout are written as ``entity="auth"``
entries so operators can detect brute-force attempts and account-takeover.
The API response stays generic (no user enumeration); only the internal
audit entry records the cause.
"""

from conftest import API, TEST_PASSWORD, auth_headers, login, make_tokens, seed_user


async def _auth_audit(client, admin_token) -> list[dict]:
    """All ``entity="auth"`` audit entries, newest first."""
    resp = await client.get(
        f"{API}/audit-logs/",
        params={"entity": "auth", "page_size": 200},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["items"]


def _find(items: list[dict], action: str, **changes) -> dict | None:
    for item in items:
        if item["action"] != action:
            continue
        item_changes = item.get("changes") or {}
        if all(item_changes.get(k) == v for k, v in changes.items()):
            return item
    return None


async def test_login_success_is_audited(client, db):
    await seed_user(db, email="ok@test.com")
    await login(client, "ok@test.com")
    tokens = await make_tokens(client, db)

    items = await _auth_audit(client, tokens["admin"])
    entry = next(
        (
            i
            for i in items
            if i["action"] == "auth.login.success" and i["user_email"] == "ok@test.com"
        ),
        None,
    )
    assert entry is not None, f"no auth.login.success for ok@test.com in {items}"


async def test_failed_login_invalid_credentials_is_audited(client, db):
    await seed_user(db, email="ok@test.com")
    resp = await client.post(
        f"{API}/auth/login", json={"email": "ok@test.com", "password": "wrong-password"}
    )
    assert resp.status_code == 401
    tokens = await make_tokens(client, db)

    items = await _auth_audit(client, tokens["admin"])
    entry = _find(items, "auth.login.failure", reason="invalid_credentials")
    assert entry is not None, f"no invalid_credentials failure in {items}"
    assert entry["user_email"] == "ok@test.com"


async def test_failed_login_unknown_user_is_audited(client, db):
    resp = await client.post(
        f"{API}/auth/login",
        json={"email": "ghost@test.com", "password": TEST_PASSWORD},
    )
    assert resp.status_code == 401
    tokens = await make_tokens(client, db)

    items = await _auth_audit(client, tokens["admin"])
    entry = _find(items, "auth.login.failure", reason="unknown_user")
    assert entry is not None, f"no unknown_user failure in {items}"
    # No user to attribute it to.
    assert entry["user_email"] is None
    assert entry["user_id"] is None


async def test_deactivated_login_is_audited(client, db):
    await seed_user(db, email="off@test.com", is_active=False)
    resp = await client.post(
        f"{API}/auth/login", json={"email": "off@test.com", "password": TEST_PASSWORD}
    )
    assert resp.status_code == 403
    tokens = await make_tokens(client, db)

    items = await _auth_audit(client, tokens["admin"])
    entry = _find(items, "auth.login.failure", reason="deactivated")
    assert entry is not None, f"no deactivated failure in {items}"


async def test_logout_is_audited(client, db):
    user = await seed_user(db, email="bye@test.com")
    tokens = await login(client, "bye@test.com")
    admin = await make_tokens(client, db)

    resp = await client.post(
        f"{API}/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert resp.status_code == 200

    items = await _auth_audit(client, admin["admin"])
    entry = _find(items, "auth.logout")
    assert entry is not None, f"no auth.logout in {items}"
    assert entry["user_email"] == "bye@test.com"
