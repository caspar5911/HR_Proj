"""Tests for the /attendance endpoints: clock in/out, month views, team rollup."""

from datetime import date

from conftest import API, auth_headers, login, seed_employee, seed_user

BASE = f"{API}/attendance"


async def _employee_tokens(client, db, email="sam@test.com"):
    """Seed an employee-role user with a linked Employee profile + token."""
    user = await seed_user(db, email=email, role="employee")
    emp = await seed_employee(db, user=user, email=f"{email.split('@')[0]}@acme.co")
    token = (await login(client, email))["access_token"]
    return emp, token


# ── clock in / clock out (POST /me) ──────────────────────────────────────────


async def test_clock_in_creates_open_day(client, db):
    emp, token = await _employee_tokens(client, db)
    resp = await client.post(
        f"{BASE}/me",
        json={"work_date": date(2026, 8, 10).isoformat(), "clock_in": "09:00:00"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["employee_id"] == emp.id
    assert body["work_date"] == "2026-08-10"
    assert body["clock_out"] is None
    assert body["hours"] is None


async def test_clock_out_computes_hours(client, db):
    emp, token = await _employee_tokens(client, db)
    await client.post(
        f"{BASE}/me",
        json={"work_date": "2026-08-10", "clock_in": "09:00:00"},
        headers=auth_headers(token),
    )
    resp = await client.post(
        f"{BASE}/me",
        json={"work_date": "2026-08-10", "clock_in": "09:00:00", "clock_out": "17:30:00", "breaks_minutes": 30},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    # 8h30m minus a 30m break = 8.0h
    assert body["hours"] == 8.0
    assert body["employee_name"] == "Ada Lovelace"


async def test_re_clock_in_kept_after_day_closed(client, db):
    """Once a day is closed, re-sending a different clock_in must not move it."""
    emp, token = await _employee_tokens(client, db)
    await client.post(
        f"{BASE}/me",
        json={"work_date": "2026-08-10", "clock_in": "08:00:00", "clock_out": "16:00:00"},
        headers=auth_headers(token),
    )
    resp = await client.post(
        f"{BASE}/me",
        json={"work_date": "2026-08-10", "clock_in": "11:00:00"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201
    body = resp.json()
    # Day stays closed on the original times; the new clock_in is ignored.
    assert body["clock_in"] == "08:00:00"
    assert body["clock_out"] == "16:00:00"
    assert body["hours"] == 8.0


async def test_cross_midnight_shift_hours(client, db):
    emp, token = await _employee_tokens(client, db)
    resp = await client.post(
        f"{BASE}/me",
        json={"work_date": "2026-08-10", "clock_in": "22:00:00", "clock_out": "06:00:00"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["hours"] == 8.0


async def test_clock_out_same_as_clock_in_rejected(client, db):
    _, token = await _employee_tokens(client, db)
    resp = await client.post(
        f"{BASE}/me",
        json={"work_date": "2026-08-10", "clock_in": "09:00:00", "clock_out": "09:00:00"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "VALIDATION_ERROR"


async def test_record_time_requires_employee_profile(client, db):
    """Authenticated user without a linked Employee profile gets a 403."""
    await seed_user(db, email="nolink@test.com", role="employee")
    token = (await login(client, "nolink@test.com"))["access_token"]
    resp = await client.post(
        f"{BASE}/me",
        json={"work_date": "2026-08-10", "clock_in": "09:00:00"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "PERMISSION_DENIED"


# ── month view (GET /me) ─────────────────────────────────────────────────────


async def test_my_month_attendance_totals(client, db):
    emp, token = await _employee_tokens(client, db)
    for day, ci, co in (
        (10, "09:00:00", "17:00:00"),
        (11, "09:30:00", "18:30:00"),
        (12, "09:00:00", None),  # open day, no hours
    ):
        payload = {"work_date": f"2026-08-{day:02d}", "clock_in": ci}
        if co:
            payload["clock_out"] = co
        resp = await client.post(f"{BASE}/me", json=payload, headers=auth_headers(token))
        assert resp.status_code == 201, resp.text

    resp = await client.get(
        f"{BASE}/me",
        params={"year": 2026, "month": 8},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["days_recorded"] == 3
    assert body["total_hours"] == 17.0  # 8 + 9; open day contributes nothing
    assert body["avg_daily_hours"] == 8.5
    assert [i["work_date"] for i in body["items"]] == [
        "2026-08-10", "2026-08-11", "2026-08-12",
    ]


async def test_my_month_attendance_requires_auth(client, db):
    await _employee_tokens(client, db)
    resp = await client.get(f"{BASE}/me")
    assert resp.status_code == 401


# ── team view (GET /team) ────────────────────────────────────────────────────


async def _employee_tokens_named(client, db, email, first, last):
    user = await seed_user(db, email=email, role="employee")
    emp = await seed_employee(
        db,
        first_name=first,
        last_name=last,
        email=f"{email.split('@')[0]}@acme.co",
        user=user,
    )
    token = (await login(client, email))["access_token"]
    return emp, token


async def test_team_attendance_rollup(client, db):
    admin = await seed_user(db, email="boss@test.com", role="admin")
    admin_token = (await login(client, "boss@test.com"))["access_token"]
    emp_a, sam_token = await _employee_tokens_named(
        client, db, "sam@test.com", "Sam", "Okafor"
    )
    emp_b, priya_token = await _employee_tokens_named(
        client, db, "priya@test.com", "Priya", "Sharma"
    )

    # Sam: two 8h days. Priya: one 10h day (2h overtime).
    sam = {"work_date": "2026-08-10", "clock_in": "09:00:00", "clock_out": "17:00:00"}
    priya = {"work_date": "2026-08-10", "clock_in": "08:00:00", "clock_out": "18:00:00"}
    for payload, tok in (
        (sam, sam_token),
        ({**sam, "work_date": "2026-08-11"}, sam_token),
        (priya, priya_token),
    ):
        resp = await client.post(f"{BASE}/me", json=payload, headers=auth_headers(tok))
        assert resp.status_code == 201, resp.text

    resp = await client.get(
        f"{BASE}/team",
        params={"year": 2026, "month": 8},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    rows = {r["employee_id"]: r for r in resp.json()}
    assert set(rows) == {emp_a.id, emp_b.id}

    a = rows[emp_a.id]
    assert a["employee_name"] == "Sam Okafor"
    assert a["days_recorded"] == 2
    assert a["total_hours"] == 16.0
    assert a["avg_daily_hours"] == 8.0
    assert a["overtime_hours"] == 0.0

    b = rows[emp_b.id]
    assert b["employee_name"] == "Priya Sharma"
    assert b["total_hours"] == 10.0
    assert b["overtime_hours"] == 2.0


async def test_team_attendance_rejects_employee_role(client, db):
    _, token = await _employee_tokens(client, db)
    resp = await client.get(f"{BASE}/team", headers=auth_headers(token))
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "FORBIDDEN"


async def test_team_attendance_empty_month(client, db):
    admin = await seed_user(db, email="boss@test.com", role="admin")
    admin_token = (await login(client, "boss@test.com"))["access_token"]
    resp = await client.get(
        f"{BASE}/team", params={"year": 2026, "month": 1}, headers=auth_headers(admin_token)
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ── per-employee month view (GET /employee/{id}) ────────────────────────────


async def test_employee_month_attendance_manager_access(client, db):
    emp, token = await _employee_tokens(client, db)
    manager = await seed_user(db, email="mgr@test.com", role="manager")
    manager_token = (await login(client, "mgr@test.com"))["access_token"]

    await client.post(
        f"{BASE}/me",
        json={"work_date": "2026-08-10", "clock_in": "09:00:00", "clock_out": "17:00:00"},
        headers=auth_headers(token),
    )

    resp = await client.get(
        f"{BASE}/employee/{emp.id}",
        params={"year": 2026, "month": 8},
        headers=auth_headers(manager_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["days_recorded"] == 1
    assert body["total_hours"] == 8.0
    assert body["items"][0]["employee_name"] == "Ada Lovelace"


async def test_employee_month_attendance_rejects_employee_role(client, db):
    emp, token = await _employee_tokens(client, db)
    resp = await client.get(
        f"{BASE}/employee/{emp.id}", headers=auth_headers(token)
    )
    assert resp.status_code == 403


# ── audit trail ──────────────────────────────────────────────────────────────


async def test_time_entry_writes_audit_log(client, db):
    _, token = await _employee_tokens(client, db)
    await client.post(
        f"{BASE}/me",
        json={"work_date": "2026-08-10", "clock_in": "09:00:00"},
        headers=auth_headers(token),
    )
    admin = await seed_user(db, email="boss@test.com", role="admin")
    admin_token = (await login(client, "boss@test.com"))["access_token"]

    resp = await client.get(
        f"{API}/audit-logs/", params={"entity": "time_entry"}, headers=auth_headers(admin_token)
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert any(i["action"] == "time_entry.recorded" for i in items)
