"""Self-service password change must be safe and audited.

Changing the password is a second-factor operation: the caller must prove they
know the *current* password, so a stolen access token alone cannot reset the
account. The new password must meet the minimum-length policy, and a successful
change is written to the audit trail (``auth.password.change``).

A password rotation also bumps the user's token version, so every access and
refresh token minted before the change is rejected on its next use — older
sessions end the moment the credential does.
"""

from conftest import API, TEST_PASSWORD, auth_headers, login, seed_user


NEW_PASSWORD = "new-password-456"


async def _change(client, token, current: str, new: str):
    return await client.post(
        f"{API}/auth/change-password",
        json={"current_password": current, "new_password": new},
        headers=auth_headers(token),
    )


async def test_change_password_success(client, db):
    await seed_user(db, email="pw@test.com")
    tokens = await login(client, "pw@test.com")

    resp = await _change(client, tokens["access_token"], TEST_PASSWORD, NEW_PASSWORD)
    assert resp.status_code == 200, resp.text

    # The new password works...
    new_tokens = await login(client, "pw@test.com", NEW_PASSWORD)
    assert new_tokens["access_token"]
    # ...and the old one is dead.
    resp = await client.post(
        f"{API}/auth/login", json={"email": "pw@test.com", "password": TEST_PASSWORD}
    )
    assert resp.status_code == 401


async def test_change_password_wrong_current_is_rejected(client, db):
    await seed_user(db, email="pw2@test.com")
    tokens = await login(client, "pw2@test.com")

    resp = await _change(client, tokens["access_token"], "not-the-password", NEW_PASSWORD)
    assert resp.status_code == 400, resp.text
    # Errors are wrapped: {"detail": {"code", "message"}}.
    assert "Current password" in resp.json()["detail"]["message"]

    # The password was NOT changed: the original still works.
    await login(client, "pw2@test.com", TEST_PASSWORD)


async def test_change_password_too_short_new_is_rejected(client, db):
    await seed_user(db, email="pw3@test.com")
    tokens = await login(client, "pw3@test.com")

    resp = await _change(client, tokens["access_token"], TEST_PASSWORD, "short")
    assert resp.status_code == 400, resp.text
    assert "at least" in resp.json()["detail"]["message"]

    # The password was NOT changed.
    await login(client, "pw3@test.com", TEST_PASSWORD)


async def test_change_password_requires_auth(client, db):
    await seed_user(db, email="pw4@test.com")
    # No bearer token at all → 401 from the auth dependency.
    resp = await _change(client, "", TEST_PASSWORD, NEW_PASSWORD)
    assert resp.status_code == 401


async def test_change_password_is_audited(client, db):
    await seed_user(db, email="admin@test.com", role="admin")
    await seed_user(db, email="pw5@test.com", role="employee")
    admin = await login(client, "admin@test.com")
    user = await login(client, "pw5@test.com")

    resp = await _change(client, user["access_token"], TEST_PASSWORD, NEW_PASSWORD)
    assert resp.status_code == 200, resp.text

    items_resp = await client.get(
        f"{API}/audit-logs/",
        params={"entity": "auth", "page_size": 200},
        headers=auth_headers(admin["access_token"]),
    )
    assert items_resp.status_code == 200, items_resp.text
    items = items_resp.json()["items"]
    entry = next((i for i in items if i["action"] == "auth.password.change"), None)
    assert entry is not None, f"no auth.password.change in {items}"
    assert entry["user_email"] == "pw5@test.com"


async def test_change_password_invalidates_prior_access_tokens(client, db):
    await seed_user(db, email="pw6@test.com")
    tokens = await login(client, "pw6@test.com")
    old_access = tokens["access_token"]

    resp = await _change(client, old_access, TEST_PASSWORD, NEW_PASSWORD)
    assert resp.status_code == 200, resp.text

    # The pre-change access token no longer resolves to the user.
    resp = await client.get(f"{API}/auth/me", headers=auth_headers(old_access))
    assert resp.status_code == 401, resp.text


async def test_change_password_invalidates_prior_refresh_tokens(client, db):
    await seed_user(db, email="pw7@test.com")
    tokens = await login(client, "pw7@test.com")

    resp = await _change(client, tokens["access_token"], TEST_PASSWORD, NEW_PASSWORD)
    assert resp.status_code == 200, resp.text

    # The pre-change refresh token can no longer be rotated into a new pair.
    resp = await client.post(
        f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert resp.status_code == 401, resp.text
    assert "sign in" in resp.json()["detail"]["message"]


async def test_change_password_new_session_is_unaffected(client, db):
    await seed_user(db, email="pw8@test.com")
    tokens = await login(client, "pw8@test.com")

    resp = await _change(client, tokens["access_token"], TEST_PASSWORD, NEW_PASSWORD)
    assert resp.status_code == 200, resp.text

    new_tokens = await login(client, "pw8@test.com", NEW_PASSWORD)
    # The freshly issued access token works...
    me = await client.get(
        f"{API}/auth/me", headers=auth_headers(new_tokens["access_token"])
    )
    assert me.status_code == 200, me.text
    # ...and its refresh token still rotates.
    resp = await client.post(
        f"{API}/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]
