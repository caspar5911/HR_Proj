"""Tests for the /employees endpoints: CRUD, filters, roles, audit trail."""

import pytest
from sqlalchemy import select

from app.models.user import User

from conftest import (
    API,
    TEST_PASSWORD,
    auth_headers,
    login,
    make_tokens,
    seed_employee,
    seed_user,
)

BASE = f"{API}/employees"

EMP_PAYLOAD = {
    "first_name": "Grace",
    "last_name": "Hopper",
    "email": "grace@acme.co",
    "department": "Engineering",
    "position": "Engineer",
    "salary_base": 6000.0,
}


# ── create ───────────────────────────────────────────────────────────────────


async def test_create_employee_as_admin(client, db):
    tokens = await make_tokens(client, db)
    resp = await client.post(BASE, json=EMP_PAYLOAD, headers=auth_headers(tokens["admin"]))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["first_name"] == "Grace"
    assert body["email"] == "grace@acme.co"
    assert body["status"] == "active"
    assert body["salary_base"] == 6000.0
    assert body["id"] > 0


async def test_create_employee_rejects_employee_role(client, db):
    tokens = await make_tokens(client, db)
    resp = await client.post(BASE, json=EMP_PAYLOAD, headers=auth_headers(tokens["employee"]))
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "FORBIDDEN"


async def test_create_employee_requires_auth(client, db):
    await make_tokens(client, db)
    resp = await client.post(BASE, json=EMP_PAYLOAD)
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "UNAUTHORIZED"


async def test_create_employee_duplicate_email_conflicts(client, db):
    tokens = await make_tokens(client, db)
    resp = await client.post(BASE, json=EMP_PAYLOAD, headers=auth_headers(tokens["admin"]))
    assert resp.status_code == 201
    dup = await client.post(BASE, json=EMP_PAYLOAD, headers=auth_headers(tokens["admin"]))
    assert dup.status_code == 409
    assert dup.json()["detail"]["code"] == "CONFLICT"


async def test_create_employee_unknown_manager_id_404(client, db):
    tokens = await make_tokens(client, db)
    payload = {**EMP_PAYLOAD, "manager_id": 9999, "email": "mgr@acme.co"}
    resp = await client.post(BASE, json=payload, headers=auth_headers(tokens["admin"]))
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "NOT_FOUND"


# ── list ─────────────────────────────────────────────────────────────────────


async def test_list_employees_pagination(client, db):
    tokens = await make_tokens(client, db)
    for i in range(5):
        await seed_employee(
            db,
            first_name=f"Emp{i}",
            email=f"emp{i}@acme.co",
            department="Ops",
        )
    resp = await client.get(
        BASE, params={"page": 1, "page_size": 2}, headers=auth_headers(tokens["admin"])
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2
    assert body["total_pages"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 2


async def test_list_employees_search_by_name_or_email(client, db):
    tokens = await make_tokens(client, db)
    await seed_employee(db, first_name="Alice", last_name="Smith", email="alice@acme.co")
    await seed_employee(db, first_name="Bob", last_name="Jones", email="bob@acme.co")
    resp = await client.get(
        BASE, params={"search": "alice"}, headers=auth_headers(tokens["admin"])
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "alice@acme.co"


async def test_list_employees_filter_by_status(client, db):
    tokens = await make_tokens(client, db)
    await seed_employee(db, email="onleave@acme.co", status="on_leave")
    await seed_employee(db, email="inactive@acme.co", status="inactive")
    resp = await client.get(
        BASE, params={"status": "on_leave"}, headers=auth_headers(tokens["admin"])
    )
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "onleave@acme.co"

    # Inactive employees are hidden from the directory list by default.
    resp = await client.get(
        BASE, params={"status": "inactive"}, headers=auth_headers(tokens["admin"])
    )
    assert resp.json()["total"] == 0


async def test_list_employees_requires_auth(client, db):
    await make_tokens(client, db)
    resp = await client.get(BASE)
    assert resp.status_code == 401


# ── role scoping (self-service vs. directory) ───────────────────────────────


async def test_employee_list_scoped_to_own_record(client, db):
    """A plain employee sees only their own record in the directory."""
    me_user = await seed_user(db, email="me@test.com", role="employee")
    other_user = await seed_user(db, email="other@test.com", role="employee")
    my_record = await seed_employee(db, first_name="Me", email="me-emp@acme.co", user=me_user)
    await seed_employee(db, first_name="Other", email="other-emp@acme.co", user=other_user)

    tokens = await login(client, "me@test.com")
    resp = await client.get(BASE, headers=auth_headers(tokens["access_token"]))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == my_record.id
    assert body["items"][0]["email"] == "me-emp@acme.co"


async def test_employee_cannot_read_other_employee(client, db):
    me_user = await seed_user(db, email="me@test.com", role="employee")
    other_user = await seed_user(db, email="other@test.com", role="employee")
    await seed_employee(db, email="me-emp@acme.co", user=me_user)
    other_record = await seed_employee(db, email="other-emp@acme.co", user=other_user)

    tokens = await login(client, "me@test.com")
    resp = await client.get(
        f"{BASE}/{other_record.id}", headers=auth_headers(tokens["access_token"])
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "PERMISSION_DENIED"


async def test_employee_can_read_own_record(client, db):
    me_user = await seed_user(db, email="me@test.com", role="employee")
    my_record = await seed_employee(db, email="me-emp@acme.co", user=me_user)

    tokens = await login(client, "me@test.com")
    resp = await client.get(f"{BASE}/{my_record.id}", headers=auth_headers(tokens["access_token"]))
    assert resp.status_code == 200
    assert resp.json()["email"] == "me-emp@acme.co"


async def test_org_tree_forbidden_for_employee(client, db):
    tokens = await make_tokens(client, db)
    resp = await client.get(f"{BASE}/org-tree", headers=auth_headers(tokens["employee"]))
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "PERMISSION_DENIED"


async def test_org_tree_allowed_for_manager(client, db):
    tokens = await make_tokens(client, db)
    resp = await client.get(f"{BASE}/org-tree", headers=auth_headers(tokens["manager"]))
    assert resp.status_code == 200


# ── detail / update ──────────────────────────────────────────────────────────


async def test_get_employee(client, db):
    tokens = await make_tokens(client, db)
    emp = await seed_employee(db)
    resp = await client.get(f"{BASE}/{emp.id}", headers=auth_headers(tokens["admin"]))
    assert resp.status_code == 200
    assert resp.json()["email"] == emp.email


async def test_get_unknown_employee_404(client, db):
    tokens = await make_tokens(client, db)
    resp = await client.get(f"{BASE}/9999", headers=auth_headers(tokens["admin"]))
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "NOT_FOUND"


async def test_update_employee_partial_preserves_other_fields(client, db):
    tokens = await make_tokens(client, db)
    emp = await seed_employee(db, salary_base=1000.0)
    resp = await client.put(
        f"{BASE}/{emp.id}", json={"salary_base": 1500.0}, headers=auth_headers(tokens["admin"])
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["salary_base"] == 1500.0
    assert body["first_name"] == "Ada"  # untouched field survives


async def test_update_employee_email_conflict(client, db):
    tokens = await make_tokens(client, db)
    await seed_employee(db, email="taken@acme.co")
    emp = await seed_employee(db, email="other@acme.co")
    resp = await client.put(
        f"{BASE}/{emp.id}", json={"email": "taken@acme.co"}, headers=auth_headers(tokens["admin"])
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "CONFLICT"


# ── deactivate / restore / delete ───────────────────────────────────────────


async def test_deactivate_and_restore_employee(client, db):
    tokens = await make_tokens(client, db)
    emp = await seed_employee(db)
    resp = await client.patch(
        f"{BASE}/{emp.id}/deactivate", headers=auth_headers(tokens["admin"])
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "inactive"

    resp = await client.patch(f"{BASE}/{emp.id}/restore", headers=auth_headers(tokens["admin"]))
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


async def test_deactivate_rejects_manager_role(client, db):
    tokens = await make_tokens(client, db)
    emp = await seed_employee(db)
    resp = await client.patch(
        f"{BASE}/{emp.id}/deactivate", headers=auth_headers(tokens["manager"])
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "FORBIDDEN"


async def test_delete_employee(client, db):
    tokens = await make_tokens(client, db)
    emp = await seed_employee(db)
    resp = await client.delete(f"{BASE}/{emp.id}", headers=auth_headers(tokens["admin"]))
    assert resp.status_code == 204

    resp = await client.get(f"{BASE}/{emp.id}", headers=auth_headers(tokens["admin"]))
    assert resp.status_code == 404


# ── offboarding: keep the linked login account in line ──────────────────────


async def _linked_user_is_active(db, user_id: int) -> bool:
    result = await db.execute(select(User).where(User.id == user_id))
    return bool(result.scalar_one().is_active)


async def test_deactivate_employee_disables_linked_account(client, db):
    """Deactivating an employee must disable their login account too."""
    leaver = await seed_user(db, email="leaver@test.com", role="employee")
    emp = await seed_employee(db, first_name="Lea", email="lea@acme.co", user=leaver)
    tokens = await make_tokens(client, db)

    resp = await client.patch(
        f"{BASE}/{emp.id}/deactivate", headers=auth_headers(tokens["admin"])
    )
    assert resp.status_code == 200

    assert await _linked_user_is_active(db, leaver.id) is False
    # ...so it can no longer authenticate.
    denied = await client.post(
        f"{API}/auth/login", json={"email": "leaver@test.com", "password": TEST_PASSWORD}
    )
    assert denied.status_code == 403


async def test_restore_employee_reenables_linked_account(client, db):
    leaver = await seed_user(db, email="leaver@test.com", role="employee")
    emp = await seed_employee(db, first_name="Lea", email="lea@acme.co", user=leaver)
    tokens = await make_tokens(client, db)

    await client.patch(f"{BASE}/{emp.id}/deactivate", headers=auth_headers(tokens["admin"]))
    assert await _linked_user_is_active(db, leaver.id) is False

    resp = await client.patch(
        f"{BASE}/{emp.id}/restore", headers=auth_headers(tokens["admin"])
    )
    assert resp.status_code == 200
    assert await _linked_user_is_active(db, leaver.id) is True


async def test_delete_employee_disables_linked_account(client, db):
    leaver = await seed_user(db, email="leaver@test.com", role="employee")
    emp = await seed_employee(db, first_name="Lea", email="lea@acme.co", user=leaver)
    tokens = await make_tokens(client, db)

    resp = await client.delete(f"{BASE}/{emp.id}", headers=auth_headers(tokens["admin"]))
    assert resp.status_code == 204
    assert await _linked_user_is_active(db, leaver.id) is False


# ── audit trail ──────────────────────────────────────────────────────────────


async def test_employee_mutation_audit_trail(client, db):
    tokens = await make_tokens(client, db)
    admin = auth_headers(tokens["admin"])

    created = await client.post(BASE, json=EMP_PAYLOAD, headers=admin)
    emp_id = created.json()["id"]
    await client.put(f"{BASE}/{emp_id}", json={"position": "Staff Engineer"}, headers=admin)
    await client.delete(f"{BASE}/{emp_id}", headers=admin)

    resp = await client.get(
        f"{API}/audit-logs/", params={"entity": "employee"}, headers=admin
    )
    assert resp.status_code == 200
    body = resp.json()
    actions = [item["action"] for item in body["items"]]
    assert "employee.created" in actions
    assert "employee.updated" in actions
    assert "employee.deleted" in actions
    assert body["total"] == 3

    # Spot-check the update entry captured old -> new values
    update_entry = next(i for i in body["items"] if i["action"] == "employee.updated")
    assert update_entry["changes"]["old"]["position"] == "Engineer"
    assert update_entry["changes"]["new"]["position"] == "Staff Engineer"
    assert update_entry["user_email"] == "admin@test.com"


async def test_audit_log_captures_numeric_change(client, db):
    """Regression: salary_base comes back from the DB as Decimal, which the
    JSON audit column cannot serialise. The audit write must still succeed and
    store plain numbers (a swallowed audit failure used to roll the session
    back and expire every instance in it)."""
    tokens = await make_tokens(client, db)
    admin = auth_headers(tokens["admin"])
    emp = await seed_employee(db, salary_base=1000.0)

    resp = await client.put(
        f"{BASE}/{emp.id}", json={"salary_base": 2000.0}, headers=admin
    )
    assert resp.status_code == 200, resp.text

    logs = await client.get(
        f"{API}/audit-logs/", params={"entity": "employee"}, headers=admin
    )
    assert logs.status_code == 200
    entry = next(i for i in logs.json()["items"] if i["action"] == "employee.updated")
    assert entry["changes"]["old"]["salary_base"] == 1000.0
    assert entry["changes"]["new"]["salary_base"] == 2000.0
