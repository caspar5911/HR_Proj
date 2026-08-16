"""API tests for goal (OKR) endpoints.

Covers role scoping (admin / manager / employee) for create, list, update
and delete, the completed lifecycle side-effects, and the audit trail.
"""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.employee import Employee
from app.models.goal import Goal
from tests.conftest import API, auth_headers, login, seed_employee, seed_user


async def _seed_org(db: AsyncSession) -> dict:
    """Seed one user per role plus their employee profiles.

    ``manager`` (Elena, Elena's profile), ``sam`` (Sam, Elena's direct
    report with a login account), ``liam`` (direct report with NO login),
    ``jordan`` (admin's profile).
    """
    admin = await seed_user(db, "admin@test.com", "admin")
    manager = await seed_user(db, "manager@test.com", "manager")
    employee = await seed_user(db, "employee@test.com", "employee")

    manager_emp = await seed_employee(
        db, "Elena", "Petrova", email="elena@acme.co", user=manager
    )
    sam = await seed_employee(
        db, "Sam", "Okafor", email="sam@acme.co", user=employee
    )
    liam = await seed_employee(db, "Liam", "Nguyen", email="liam@acme.co")
    jordan = await seed_employee(
        db, "Jordan", "Avery", email="jordan@acme.co", user=admin
    )

    sam.manager_id = manager_emp.id
    liam.manager_id = manager_emp.id
    await db.commit()

    return {
        "users": {"admin": admin, "manager": manager, "employee": employee},
        "employees": {
            "manager": manager_emp,
            "sam": sam,
            "liam": liam,
            "jordan": jordan,
        },
    }


def _make_goal(employee: Employee, title: str, period: str = "H2 2026",
               progress: int = 0, status: str = "active") -> Goal:
    """Build (don't persist) a Goal for the given employee."""
    return Goal(
        employee_id=employee.id,
        title=title,
        period=period,
        progress=progress,
        status=status,
    )


def _payload(employee_id: int, **kw) -> dict:
    base = {
        "employee_id": employee_id,
        "title": "Ship the quarterly report",
        "period": "H2 2026",
        "progress": 0,
    }
    base.update(kw)
    return base


# ── create scoping ───────────────────────────────────────────────────────────


async def test_create_goal_scoping(client: AsyncClient, db: AsyncSession):
    org = await _seed_org(db)
    users, emps = org["users"], org["employees"]
    sam, liam, jordan = emps["sam"], emps["liam"], emps["jordan"]

    employee_tok = (await login(client, users["employee"].email))["access_token"]
    manager_tok = (await login(client, users["manager"].email))["access_token"]
    admin_tok = (await login(client, users["admin"].email))["access_token"]

    # Unauthenticated
    resp = await client.post(f"{API}/goals/", json=_payload(sam.id))
    assert resp.status_code == 401

    # Employee: own goal OK, another employee's goal -> 403
    resp = await client.post(
        f"{API}/goals/", json=_payload(sam.id), headers=auth_headers(employee_tok)
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["employee_name"] == "Sam Okafor"

    resp = await client.post(
        f"{API}/goals/", json=_payload(liam.id), headers=auth_headers(employee_tok)
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "PERMISSION_DENIED"

    # Manager: direct report OK, non-report -> 403
    resp = await client.post(
        f"{API}/goals/", json=_payload(sam.id), headers=auth_headers(manager_tok)
    )
    assert resp.status_code == 201, resp.text

    resp = await client.post(
        f"{API}/goals/", json=_payload(jordan.id), headers=auth_headers(manager_tok)
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "PERMISSION_DENIED"

    # Admin: anyone
    resp = await client.post(
        f"{API}/goals/", json=_payload(jordan.id), headers=auth_headers(admin_tok)
    )
    assert resp.status_code == 201, resp.text


async def test_create_goal_validation(client: AsyncClient, db: AsyncSession):
    org = await _seed_org(db)
    admin_tok = (await login(client, org["users"]["admin"].email))["access_token"]
    headers = auth_headers(admin_tok)
    sam = org["employees"]["sam"]

    # progress > 100 rejected (422)
    resp = await client.post(f"{API}/goals/", json=_payload(sam.id, progress=101),
                             headers=headers)
    assert resp.status_code == 422, resp.text

    # too-short title rejected (422)
    resp = await client.post(f"{API}/goals/", json=_payload(sam.id, title="ab"),
                             headers=headers)
    assert resp.status_code == 422, resp.text


# ── list scoping + filters ───────────────────────────────────────────────────


async def test_list_goals_scoped_by_role(client: AsyncClient, db: AsyncSession):
    org = await _seed_org(db)
    users, emps = org["users"], org["employees"]
    sam, liam, manager_emp, jordan = (
        emps["sam"], emps["liam"], emps["manager"], emps["jordan"])

    db.add(_make_goal(sam, "Sam H2 goal", "H2 2026", 40))
    db.add(_make_goal(sam, "Sam H1 goal", "H1 2026", 100, "completed"))
    db.add(_make_goal(liam, "Liam goal", "H2 2026", 10))
    db.add(_make_goal(manager_emp, "Elena goal", "H2 2026", 60))
    db.add(_make_goal(jordan, "Jordan goal", "H2 2026", 5, "archived"))
    await db.commit()

    employee_tok = (await login(client, users["employee"].email))["access_token"]
    manager_tok = (await login(client, users["manager"].email))["access_token"]
    admin_tok = (await login(client, users["admin"].email))["access_token"]

    # Employee sees only Sam's two goals
    resp = await client.get(f"{API}/goals/", headers=auth_headers(employee_tok))
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 2
    assert {g["title"] for g in resp.json()} == {"Sam H2 goal", "Sam H1 goal"}

    # Manager sees Sam (2) + Liam (1) + self (1) = 4, not Jordan
    resp = await client.get(f"{API}/goals/", headers=auth_headers(manager_tok))
    assert len(resp.json()) == 4
    assert not any(g["title"] == "Jordan goal" for g in resp.json())

    # Admin sees all 5
    resp = await client.get(f"{API}/goals/", headers=auth_headers(admin_tok))
    assert len(resp.json()) == 5

    # Period filter (admin, H2 2026 -> 4: Sam H2, Liam, Elena, Jordan)
    resp = await client.get(
        f"{API}/goals/?period=H2 2026", headers=auth_headers(admin_tok))
    assert len(resp.json()) == 4

    # Status filter (admin, completed -> Sam H1 only)
    resp = await client.get(
        f"{API}/goals/?status=completed", headers=auth_headers(admin_tok))
    assert len(resp.json()) == 1
    assert resp.json()[0]["title"] == "Sam H1 goal"

    # Manager filtering by a non-report employee -> empty (no existence leak)
    resp = await client.get(
        f"{API}/goals/?employee_id={jordan.id}", headers=auth_headers(manager_tok))
    assert resp.json() == []


# ── update ───────────────────────────────────────────────────────────────────


async def test_update_goal_progress_and_title(client: AsyncClient, db: AsyncSession):
    org = await _seed_org(db)
    sam = org["employees"]["sam"]
    db.add(_make_goal(sam, "Ship it", "H2 2026", 0))
    await db.commit()
    goal = (await db.execute(select(Goal).where(Goal.employee_id == sam.id))).scalars().first()

    employee_tok = (await login(client, org["users"]["employee"].email))["access_token"]
    resp = await client.patch(
        f"{API}/goals/{goal.id}",
        json={"progress": 45, "title": "Ship it v2"},
        headers=auth_headers(employee_tok),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["progress"] == 45
    assert body["title"] == "Ship it v2"
    assert body["status"] == "active"
    assert body["completed_at"] is None


async def test_update_goal_mark_completed(client: AsyncClient, db: AsyncSession):
    org = await _seed_org(db)
    sam = org["employees"]["sam"]
    db.add(_make_goal(sam, "Finish the thing", "H2 2026", 30))
    await db.commit()
    goal = (await db.execute(select(Goal).where(Goal.employee_id == sam.id))).scalars().first()

    admin_tok = (await login(client, org["users"]["admin"].email))["access_token"]
    resp = await client.patch(
        f"{API}/goals/{goal.id}", json={"status": "completed"},
        headers=auth_headers(admin_tok),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "completed"
    assert body["progress"] == 100
    assert body["completed_at"] is not None


async def test_update_goal_scoping(client: AsyncClient, db: AsyncSession):
    org = await _seed_org(db)
    sam, jordan = org["employees"]["sam"], org["employees"]["jordan"]
    db.add(_make_goal(sam, "Sam goal", "H2 2026", 0))
    db.add(_make_goal(jordan, "Jordan goal", "H2 2026", 0))
    await db.commit()
    sam_goal = (await db.execute(select(Goal).where(Goal.employee_id == sam.id))).scalars().first()
    jordan_goal = (await db.execute(select(Goal).where(Goal.employee_id == jordan.id))).scalars().first()

    employee_tok = (await login(client, org["users"]["employee"].email))["access_token"]
    manager_tok = (await login(client, org["users"]["manager"].email))["access_token"]

    # Employee cannot touch another employee's goal -> 404
    resp = await client.patch(
        f"{API}/goals/{jordan_goal.id}", json={"progress": 10},
        headers=auth_headers(employee_tok),
    )
    assert resp.status_code == 404

    # Manager can edit a report's goal
    resp = await client.patch(
        f"{API}/goals/{sam_goal.id}", json={"progress": 20},
        headers=auth_headers(manager_tok),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["progress"] == 20

    # Manager cannot edit a non-report's goal -> 404
    resp = await client.patch(
        f"{API}/goals/{jordan_goal.id}", json={"progress": 20},
        headers=auth_headers(manager_tok),
    )
    assert resp.status_code == 404


# ── delete ───────────────────────────────────────────────────────────────────


async def test_delete_goal_scoping(client: AsyncClient, db: AsyncSession):
    org = await _seed_org(db)
    sam = org["employees"]["sam"]
    db.add(_make_goal(sam, "Doable goal", "H2 2026", 0))
    await db.commit()
    goal = (await db.execute(select(Goal).where(Goal.employee_id == sam.id))).scalars().first()

    manager_tok = (await login(client, org["users"]["manager"].email))["access_token"]
    admin_tok = (await login(client, org["users"]["admin"].email))["access_token"]

    # Manager can see/edit a report's goal but not delete it -> 404
    resp = await client.delete(
        f"{API}/goals/{goal.id}", headers=auth_headers(manager_tok))
    assert resp.status_code == 404

    # Admin deletes -> 204
    resp = await client.delete(
        f"{API}/goals/{goal.id}", headers=auth_headers(admin_tok))
    assert resp.status_code == 204

    # Gone now
    resp = await client.get(f"{API}/goals/", headers=auth_headers(admin_tok))
    assert resp.json() == []


# ── audit trail ──────────────────────────────────────────────────────────────


async def test_goal_audit_trail(client: AsyncClient, db: AsyncSession):
    org = await _seed_org(db)
    sam = org["employees"]["sam"]
    admin_tok = (await login(client, org["users"]["admin"].email))["access_token"]
    headers = auth_headers(admin_tok)

    resp = await client.post(f"{API}/goals/", json=_payload(sam.id, progress=10),
                             headers=headers)
    assert resp.status_code == 201, resp.text
    goal_id = resp.json()["id"]

    await client.patch(
        f"{API}/goals/{goal_id}", json={"progress": 50}, headers=headers)

    rows = (await db.execute(
        select(AuditLog).where(AuditLog.entity == "goal")
        .order_by(AuditLog.id)
    )).scalars().all()
    actions = [r.action for r in rows]
    assert "goal.created" in actions
    assert "goal.updated" in actions
