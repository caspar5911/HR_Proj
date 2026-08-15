"""API tests for performance review endpoints.

Covers role scoping (admin / manager / employee), the draft -> submitted ->
shared lifecycle, and the notification + audit trail fired on share.
"""

from datetime import date

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.employee import Employee
from app.models.notification import Notification
from app.models.review import ReviewCycle
from tests.conftest import API, auth_headers, login, seed_employee, seed_user


async def _seed_cycle(
    db: AsyncSession,
    name: str = "2026 Mid-Year Review",
    status: str = "active",
) -> ReviewCycle:
    cycle = ReviewCycle(
        name=name,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 6, 30),
        status=status,
    )
    db.add(cycle)
    await db.commit()
    await db.refresh(cycle)
    return cycle


async def _seed_org(db: AsyncSession) -> dict:
    """Seed one user per role plus their employee profiles.

    Returns ``{"users": {...}, "employees": {...}}`` where
    ``employees`` has ``manager`` (Elena, Elena's profile), ``sam``
    (Sam, direct report of Elena with a login account), ``liam``
    (direct report with NO login account) and ``jordan`` (admin's profile).
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


def _make_review(db: AsyncSession, cycle: ReviewCycle, employee: Employee, reviewer, rating: int):
    """Build (don't persist) a draft Review for the given employee."""
    from app.models.review import Review

    return Review(
        cycle_id=cycle.id,
        employee_id=employee.id,
        reviewer_user_id=reviewer.id,
        rating=rating,
        status="draft",
    )


# ── cycles ───────────────────────────────────────────────────────────────────


async def test_create_review_cycle_requires_admin(client: AsyncClient, db: AsyncSession):
    org = await _seed_org(db)
    manager_tok = (await login(client, org["users"]["manager"].email))["access_token"]
    employee_tok = (await login(client, org["users"]["employee"].email))["access_token"]

    payload = {
        "name": "2026 Mid-Year Review",
        "period_start": "2026-01-01",
        "period_end": "2026-06-30",
        "description": "Half-year check-ins",
    }

    # Unauthenticated
    resp = await client.post(f"{API}/review-cycles/", json=payload)
    assert resp.status_code == 401

    # Manager / employee are blocked (require_role -> plain 403)
    for tok in (manager_tok, employee_tok):
        resp = await client.post(
            f"{API}/review-cycles/", json=payload, headers=auth_headers(tok)
        )
        assert resp.status_code == 403, resp.text

    # Admin succeeds
    admin_tok = (await login(client, org["users"]["admin"].email))["access_token"]
    resp = await client.post(
        f"{API}/review-cycles/", json=payload, headers=auth_headers(admin_tok)
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "2026 Mid-Year Review"
    assert body["status"] == "active"
    assert body["total_reviews"] == 0
    assert body["drafts"] == 0 and body["submitted"] == 0 and body["shared"] == 0


async def test_create_review_cycle_validation(client: AsyncClient, db: AsyncSession):
    org = await _seed_org(db)
    admin_tok = (await login(client, org["users"]["admin"].email))["access_token"]
    headers = auth_headers(admin_tok)

    # Inverted period is rejected by the schema (422)
    resp = await client.post(
        f"{API}/review-cycles/",
        json={
            "name": "Backwards Cycle",
            "period_start": "2026-06-30",
            "period_end": "2026-01-01",
        },
        headers=headers,
    )
    assert resp.status_code == 422, resp.text

    # Create the cycle, then a duplicate name is a 400
    good = {
        "name": "2026 Q3 Review",
        "period_start": "2026-07-01",
        "period_end": "2026-09-30",
    }
    resp = await client.post(f"{API}/review-cycles/", json=good, headers=headers)
    assert resp.status_code == 201, resp.text
    resp = await client.post(f"{API}/review-cycles/", json=good, headers=headers)
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "VALIDATION_ERROR"


async def test_list_review_cycles_with_progress_counts(client: AsyncClient, db: AsyncSession):
    org = await _seed_org(db)
    manager = org["users"]["manager"]
    sam = org["employees"]["sam"]

    cycle = await _seed_cycle(db)
    await _seed_cycle(db, name="2025 Year-End Review")

    # One draft review in the mid-year cycle (Sam is Elena's direct report).
    db.add(_make_review(db, cycle, sam, manager, 4))
    await db.commit()

    manager_tok = (await login(client, manager.email))["access_token"]
    resp = await client.get(f"{API}/review-cycles/", headers=auth_headers(manager_tok))
    assert resp.status_code == 200, resp.text
    cycles = resp.json()
    assert len(cycles) == 2
    # Newest period first
    assert cycles[0]["name"] == "2026 Mid-Year Review"
    assert cycles[0]["total_reviews"] == 1
    assert cycles[0]["drafts"] == 1
    assert cycles[0]["submitted"] == 0


# ── creating reviews ─────────────────────────────────────────────────────────


async def test_manager_creates_review_for_direct_report(client: AsyncClient, db: AsyncSession):
    org = await _seed_org(db)
    manager = org["users"]["manager"]
    sam = org["employees"]["sam"]
    cycle = await _seed_cycle(db)

    manager_tok = (await login(client, manager.email))["access_token"]
    resp = await client.post(
        f"{API}/review-cycles/{cycle.id}/reviews/",
        json={
            "employee_id": sam.id,
            "rating": 4,
            "strengths": "Shipped the leave module on time",
            "improvements": "Pick up code review earlier",
            "goals": "Own the payroll refactor",
            "submit": True,
        },
        headers=auth_headers(manager_tok),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "submitted"
    assert body["submitted_at"] is not None
    assert body["employee_name"] == "Sam Okafor"
    assert body["cycle_name"] == "2026 Mid-Year Review"
    assert body["reviewer_name"] == "manager@test.com"
    assert body["rating"] == 4


async def test_manager_cannot_review_non_direct_report(client: AsyncClient, db: AsyncSession):
    org = await _seed_org(db)
    manager = org["users"]["manager"]
    jordan = org["employees"]["jordan"]  # has no manager -> not Elena's report
    cycle = await _seed_cycle(db)

    manager_tok = (await login(client, manager.email))["access_token"]
    resp = await client.post(
        f"{API}/review-cycles/{cycle.id}/reviews/",
        json={"employee_id": jordan.id, "rating": 5},
        headers=auth_headers(manager_tok),
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"]["code"] == "PERMISSION_DENIED"


async def test_employee_cannot_create_reviews(client: AsyncClient, db: AsyncSession):
    org = await _seed_org(db)
    employee = org["users"]["employee"]
    sam = org["employees"]["sam"]
    cycle = await _seed_cycle(db)

    employee_tok = (await login(client, employee.email))["access_token"]
    resp = await client.post(
        f"{API}/review-cycles/{cycle.id}/reviews/",
        json={"employee_id": sam.id, "rating": 3},
        headers=auth_headers(employee_tok),
    )
    assert resp.status_code == 403, resp.text


async def test_admin_can_review_anyone(client: AsyncClient, db: AsyncSession):
    org = await _seed_org(db)
    admin = org["users"]["admin"]
    jordan = org["employees"]["jordan"]
    cycle = await _seed_cycle(db)

    admin_tok = (await login(client, admin.email))["access_token"]
    resp = await client.post(
        f"{API}/review-cycles/{cycle.id}/reviews/",
        json={"employee_id": jordan.id, "rating": 5, "strengths": "Solid leadership"},
        headers=auth_headers(admin_tok),
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "draft"


async def test_review_duplicate_and_closed_cycle(client: AsyncClient, db: AsyncSession):
    org = await _seed_org(db)
    manager = org["users"]["manager"]
    sam = org["employees"]["sam"]
    cycle = await _seed_cycle(db)

    manager_tok = (await login(client, manager.email))["access_token"]
    payload = {"employee_id": sam.id, "rating": 4}
    resp = await client.post(
        f"{API}/review-cycles/{cycle.id}/reviews/",
        json=payload,
        headers=auth_headers(manager_tok),
    )
    assert resp.status_code == 201, resp.text
    # Same employee + cycle again -> 400
    resp = await client.post(
        f"{API}/review-cycles/{cycle.id}/reviews/",
        json=payload,
        headers=auth_headers(manager_tok),
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "VALIDATION_ERROR"

    # Closed cycle rejects new reviews
    closed = await _seed_cycle(db, name="2025 Year-End Review", status="closed")
    resp = await client.post(
        f"{API}/review-cycles/{closed.id}/reviews/",
        json=payload,
        headers=auth_headers(manager_tok),
    )
    assert resp.status_code == 400, resp.text
    assert "closed" in resp.json()["detail"]["message"].lower()


async def test_rating_out_of_bounds_rejected(client: AsyncClient, db: AsyncSession):
    org = await _seed_org(db)
    manager = org["users"]["manager"]
    sam = org["employees"]["sam"]
    cycle = await _seed_cycle(db)

    manager_tok = (await login(client, manager.email))["access_token"]
    resp = await client.post(
        f"{API}/review-cycles/{cycle.id}/reviews/",
        json={"employee_id": sam.id, "rating": 6},
        headers=auth_headers(manager_tok),
    )
    assert resp.status_code == 422, resp.text


# ── visibility scoping ───────────────────────────────────────────────────────


async def test_list_cycle_reviews_scoped_by_role(client: AsyncClient, db: AsyncSession):
    org = await _seed_org(db)
    manager = org["users"]["manager"]
    employee = org["users"]["employee"]
    admin = org["users"]["admin"]
    manager_emp = org["employees"]["manager"]
    sam = org["employees"]["sam"]
    liam = org["employees"]["liam"]
    jordan = org["employees"]["jordan"]
    cycle = await _seed_cycle(db)

    # Three reviews: Sam (Elena's report), Liam (Elena's report), Jordan (nobody's report)
    for emp, rating in ((sam, 4), (liam, 3), (jordan, 5)):
        db.add(_make_review(db, cycle, emp, manager, rating))
    await db.commit()

    manager_tok = (await login(client, manager.email))["access_token"]
    resp = await client.get(
        f"{API}/review-cycles/{cycle.id}/reviews/", headers=auth_headers(manager_tok)
    )
    assert resp.status_code == 200, resp.text
    names = sorted(r["employee_name"] for r in resp.json())
    assert names == ["Liam Nguyen", "Sam Okafor"]

    employee_tok = (await login(client, employee.email))["access_token"]
    resp = await client.get(
        f"{API}/review-cycles/{cycle.id}/reviews/", headers=auth_headers(employee_tok)
    )
    assert resp.status_code == 200, resp.text
    assert [r["employee_name"] for r in resp.json()] == ["Sam Okafor"]

    admin_tok = (await login(client, admin.email))["access_token"]
    resp = await client.get(
        f"{API}/review-cycles/{cycle.id}/reviews/", headers=auth_headers(admin_tok)
    )
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 3


async def test_get_review_visibility_rules(client: AsyncClient, db: AsyncSession):
    org = await _seed_org(db)
    manager = org["users"]["manager"]
    employee = org["users"]["employee"]
    sam = org["employees"]["sam"]
    liam = org["employees"]["liam"]
    cycle = await _seed_cycle(db)

    sam_review = _make_review(db, cycle, sam, manager, 4)
    liam_review = _make_review(db, cycle, liam, manager, 3)
    db.add_all([sam_review, liam_review])
    await db.commit()

    employee_tok = (await login(client, employee.email))["access_token"]
    headers = auth_headers(employee_tok)

    # Sam's own review is readable
    resp = await client.get(f"{API}/reviews/{sam_review.id}", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["strengths"] is None  # created without strengths

    # Liam's review is NOT Sam's
    resp = await client.get(f"{API}/reviews/{liam_review.id}", headers=headers)
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"]["code"] == "NOT_FOUND"

    # A manager cannot read a review about a non-direct-report
    jordan = org["employees"]["jordan"]
    jordan_review = _make_review(db, cycle, jordan, org["users"]["admin"], 5)
    db.add(jordan_review)
    await db.commit()
    manager_tok = (await login(client, manager.email))["access_token"]
    resp = await client.get(
        f"{API}/reviews/{jordan_review.id}", headers=auth_headers(manager_tok)
    )
    assert resp.status_code == 404, resp.text


# ── editing + sharing lifecycle ──────────────────────────────────────────────


async def test_update_review_by_author(client: AsyncClient, db: AsyncSession):
    org = await _seed_org(db)
    manager = org["users"]["manager"]
    sam = org["employees"]["sam"]
    cycle = await _seed_cycle(db)
    review = _make_review(db, cycle, sam, manager, 3)
    db.add(review)
    await db.commit()

    manager_tok = (await login(client, manager.email))["access_token"]
    headers = auth_headers(manager_tok)

    # Edit fields
    resp = await client.patch(
        f"{API}/reviews/{review.id}",
        json={"rating": 5, "strengths": "Outstanding work"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["rating"] == 5
    assert resp.json()["strengths"] == "Outstanding work"
    assert resp.json()["status"] == "draft"

    # Moving draft -> submitted stamps submitted_at
    resp = await client.patch(
        f"{API}/reviews/{review.id}",
        json={"status": "submitted"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "submitted"
    assert resp.json()["submitted_at"] is not None

    # Someone else (the employee) cannot edit
    employee_tok = (
        await login(client, org["users"]["employee"].email)
    )["access_token"]
    resp = await client.patch(
        f"{API}/reviews/{review.id}",
        json={"rating": 1},
        headers=auth_headers(employee_tok),
    )
    assert resp.status_code == 404, resp.text


async def test_update_shared_review_blocked(client: AsyncClient, db: AsyncSession):
    org = await _seed_org(db)
    manager = org["users"]["manager"]
    sam = org["employees"]["sam"]
    cycle = await _seed_cycle(db)
    review = _make_review(db, cycle, sam, manager, 4)
    review.status = "shared"
    db.add(review)
    await db.commit()

    manager_tok = (await login(client, manager.email))["access_token"]
    resp = await client.patch(
        f"{API}/reviews/{review.id}",
        json={"rating": 2},
        headers=auth_headers(manager_tok),
    )
    assert resp.status_code == 400, resp.text
    assert "shared" in resp.json()["detail"]["message"].lower()


async def test_share_review_full_flow(client: AsyncClient, db: AsyncSession):
    org = await _seed_org(db)
    manager = org["users"]["manager"]
    employee = org["users"]["employee"]
    sam = org["employees"]["sam"]
    cycle = await _seed_cycle(db)
    review = _make_review(db, cycle, sam, manager, 4)
    review.strengths = "Shipped the leave module"
    db.add(review)
    await db.commit()

    manager_tok = (await login(client, manager.email))["access_token"]
    headers = auth_headers(manager_tok)

    # Drafts cannot be shared yet
    resp = await client.post(f"{API}/reviews/{review.id}/share", headers=headers)
    assert resp.status_code == 400, resp.text
    assert "submit" in resp.json()["detail"]["message"].lower()

    # Submit, then share
    resp = await client.patch(
        f"{API}/reviews/{review.id}", json={"status": "submitted"}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    resp = await client.post(f"{API}/reviews/{review.id}/share", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "shared"
    assert resp.json()["shared_at"] is not None

    # A notification landed in Sam's bell
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == employee.id,
            Notification.type == "review_shared",
        )
    )
    notifs = list(result.scalars().all())
    assert len(notifs) == 1
    assert "2026 Mid-Year Review" in notifs[0].title
    assert notifs[0].link == "/my-reviews"
    assert notifs[0].read_at is None

    # Audit trail recorded the share
    result = await db.execute(
        select(AuditLog).where(
            AuditLog.action == "review.shared",
            AuditLog.entity == "review",
            AuditLog.entity_id == review.id,
        )
    )
    assert result.scalars().first() is not None

    # Sharing twice is a 400
    resp = await client.post(f"{API}/reviews/{review.id}/share", headers=headers)
    assert resp.status_code == 400, resp.text

    # A different manager (non-author, non-admin) may not share: 404
    await seed_user(db, "manager2@test.com", "manager")
    manager2_tok = (await login(client, "manager2@test.com"))["access_token"]
    resp = await client.post(
        f"{API}/reviews/{review.id}/share",
        headers=auth_headers(manager2_tok),
    )
    assert resp.status_code == 404, resp.text


async def test_share_review_without_employee_account(client: AsyncClient, db: AsyncSession):
    """Sharing still succeeds when the employee has no login account — it just
    does not create a notification (Liam has no user)."""
    org = await _seed_org(db)
    manager = org["users"]["manager"]
    liam = org["employees"]["liam"]
    assert liam.user_id is None
    cycle = await _seed_cycle(db)
    review = _make_review(db, cycle, liam, manager, 3)
    review.status = "submitted"
    db.add(review)
    await db.commit()

    manager_tok = (await login(client, manager.email))["access_token"]
    resp = await client.post(
        f"{API}/reviews/{review.id}/share",
        headers=auth_headers(manager_tok),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "shared"

    result = await db.execute(select(Notification))
    assert list(result.scalars().all()) == []
