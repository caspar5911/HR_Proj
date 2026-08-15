"""Tests for the /notifications endpoints and the in-app notification service."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.services import notifications as notify_service
from conftest import API, auth_headers, login, seed_employee, seed_leave_type, seed_user

BASE = f"{API}/notifications"


async def _team(client, db, manager_email="mgr@test.com", employee_email="sam@test.com", with_manager=True):
    """Seed a manager + employee (both with login accounts) and return tokens.

    The employee's profile points at the manager's profile so new leave
    requests route their in-app notification to the manager.
    """
    mgr_user = await seed_user(db, email=manager_email, role="manager")
    mgr_emp = await seed_employee(
        db, first_name="Elena", last_name="Petrova", email="mgr@acme.co", user=mgr_user
    )

    emp_user = await seed_user(db, email=employee_email, role="employee")
    emp_emp = await seed_employee(
        db, first_name="Sam", last_name="Okafor", email="sam@acme.co", user=emp_user
    )
    if with_manager:
        emp_emp.manager_id = mgr_emp.id
        await db.commit()

    return {
        "manager": (await login(client, manager_email))["access_token"],
        "employee": (await login(client, employee_email))["access_token"],
        "manager_employee": mgr_emp,
        "employee_employee": emp_emp,
    }


async def _create_request(client, token, leave_type_id, start="2026-09-01", end="2026-09-03"):
    resp = await client.post(
        f"{API}/leave-requests/",
        json={"leave_type_id": leave_type_id, "start_date": start, "end_date": end},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _list(client, token, **params):
    resp = await client.get(f"{BASE}/", params=params, headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


# ── event → notification flow ────────────────────────────────────────────────


async def test_create_leave_request_notifies_manager(client, db):
    lt = await seed_leave_type(db)
    team = await _team(client, db)
    await _create_request(client, team["employee"], lt.id)

    items = await _list(client, team["manager"])
    assert items["total"] == 1
    n = items["items"][0]
    assert n["type"] == "leave_requested"
    assert "Sam Okafor" in n["title"]
    assert n["read"] is False
    assert n["link"] == "/leave"

    # The submitting employee gets nothing for their own request.
    assert (await _list(client, team["employee"]))["total"] == 0


async def test_approve_leave_notifies_employee(client, db):
    lt = await seed_leave_type(db)
    team = await _team(client, db)
    req = await _create_request(client, team["employee"], lt.id)

    resp = await client.put(
        f"{API}/leave-requests/{req['id']}/approve",
        json={"status": "approved", "manager_note": "Enjoy it!"},
        headers=auth_headers(team["manager"]),
    )
    assert resp.status_code == 200, resp.text

    items = await _list(client, team["employee"])
    assert items["total"] == 1
    n = items["items"][0]
    assert n["type"] == "leave_approved"
    assert "approved" in n["title"]
    assert "Enjoy it!" in n["body"]


async def test_reject_leave_notifies_employee(client, db):
    lt = await seed_leave_type(db)
    team = await _team(client, db)
    req = await _create_request(client, team["employee"], lt.id)

    resp = await client.put(
        f"{API}/leave-requests/{req['id']}/reject",
        json={"status": "rejected", "manager_note": "Covers too tight"},
        headers=auth_headers(team["manager"]),
    )
    assert resp.status_code == 200, resp.text

    items = await _list(client, team["employee"])
    assert items["total"] == 1
    assert items["items"][0]["type"] == "leave_rejected"


async def test_employee_without_manager_account_falls_back_to_admins(client, db):
    """No manager with a login account → active managers/admins are notified."""
    lt = await seed_leave_type(db)
    team = await _team(client, db, with_manager=False)
    admin_user = await seed_user(db, email="boss@test.com", role="admin")
    admin_token = (await login(client, "boss@test.com"))["access_token"]
    # The manager account exists but the profile link is the only route;
    # deactivate it so only the admin fallback remains.
    from sqlalchemy import func, select, update

    from app.models.notification import Notification
    from app.models.user import User

    await db.execute(
        update(User).where(User.email == "mgr@test.com").values(is_active=False)
    )
    await db.commit()

    await _create_request(client, team["employee"], lt.id)

    assert (await _list(client, admin_token))["total"] == 1
    # The deactivated manager's account received nothing.
    mgr_id = (
        await db.execute(select(User.id).where(User.email == "mgr@test.com"))
    ).scalar_one()
    assert (
        await db.execute(
            select(func.count()).select_from(Notification).where(Notification.user_id == mgr_id)
        )
    ).scalar() == 0


# ── unread count + read flows ────────────────────────────────────────────────


async def test_unread_count_and_mark_read(client, db):
    lt = await seed_leave_type(db)
    team = await _team(client, db)
    await _create_request(client, team["employee"], lt.id)

    resp = await client.get(f"{BASE}/unread-count", headers=auth_headers(team["manager"]))
    assert resp.status_code == 200
    assert resp.json() == {"unread": 1}

    n = (await _list(client, team["manager"]))["items"][0]
    resp = await client.patch(
        f"{BASE}/{n['id']}/read", headers=auth_headers(team["manager"])
    )
    assert resp.status_code == 200
    assert resp.json()["read"] is True
    assert resp.json()["read_at"] is not None

    # Marking it read again is a no-op, still 200.
    resp = await client.patch(
        f"{BASE}/{n['id']}/read", headers=auth_headers(team["manager"])
    )
    assert resp.status_code == 200

    resp = await client.get(f"{BASE}/unread-count", headers=auth_headers(team["manager"]))
    assert resp.json() == {"unread": 0}


async def test_mark_all_read(client, db):
    lt = await seed_leave_type(db)
    team = await _team(client, db)
    await _create_request(client, team["employee"], lt.id, start="2026-09-01", end="2026-09-03")
    await _create_request(client, team["employee"], lt.id, start="2026-09-10", end="2026-09-12")

    resp = await client.post(f"{BASE}/read-all", headers=auth_headers(team["manager"]))
    assert resp.status_code == 200
    assert resp.json() == {"unread": 0}

    items = await _list(client, team["manager"])
    assert items["total"] == 2
    assert all(n["read"] for n in items["items"])


async def test_cannot_read_another_users_notification(client, db):
    lt = await seed_leave_type(db)
    team = await _team(client, db)
    await _create_request(client, team["employee"], lt.id)
    n = (await _list(client, team["manager"]))["items"][0]

    resp = await client.patch(
        f"{BASE}/{n['id']}/read", headers=auth_headers(team["employee"])
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "NOT_FOUND"


async def test_notifications_require_auth(client, db):
    resp = await client.get(f"{BASE}/")
    assert resp.status_code == 401
    resp = await client.get(f"{BASE}/unread-count")
    assert resp.status_code == 401


# ── payroll event (service level) ────────────────────────────────────────────


async def test_payroll_processed_notifies_each_employee(client, db):
    team = await _team(client, db)
    sam_emp = team["employee_employee"]

    second_user = await seed_user(db, email="priya@test.com", role="employee")
    priya_emp = await seed_employee(
        db, first_name="Priya", last_name="Sharma", email="priya@acme.co", user=second_user
    )
    priya_token = (await login(client, "priya@test.com"))["access_token"]

    run = SimpleNamespace(period_start=date(2026, 8, 1), period_end=date(2026, 8, 31))
    entries = [
        SimpleNamespace(employee_id=sam_emp.id, net_pay=Decimal("4200.50")),
        SimpleNamespace(employee_id=priya_emp.id, net_pay=Decimal("5000.00")),
    ]
    await notify_service.notify_payroll_processed(db, run, entries)

    items = await _list(client, team["employee"])
    assert items["total"] == 1
    n = items["items"][0]
    assert n["type"] == "payroll_processed"
    assert "August" not in n["title"]  # ISO dates, not prose
    assert "2026-08-01 to 2026-08-31" in n["title"]
    assert "4,200.50" in n["body"]
    assert n["link"] == "/my-home"

    priya_items = await _list(client, priya_token)
    assert priya_items["total"] == 1
    assert "5,000.00" in priya_items["items"][0]["body"]


async def test_payroll_notification_ignores_employees_without_accounts(db):
    """Employees without a login account are skipped without erroring."""
    sam_emp = await seed_employee(
        db, first_name="Solo", last_name="Worker", email="solo@acme.co"
    )  # no user account
    run = SimpleNamespace(period_start=date(2026, 8, 1), period_end=date(2026, 8, 31))
    entries = [SimpleNamespace(employee_id=sam_emp.id, net_pay=Decimal("3000.00"))]
    assert await notify_service.notify_payroll_processed(db, run, entries) is None
