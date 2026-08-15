"""Performance review API endpoints.

Roles:
* Admins manage cycles and every review.
* Managers write reviews for their direct reports.
* Employees read only the reviews about themselves.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, require_role
from app.models.employee import Employee
from app.models.review import Review, ReviewCycle
from app.models.user import User, UserRole
from app.schemas.review import (
    ReviewCreate,
    ReviewCycleCreate,
    ReviewCycleOut,
    ReviewOut,
    ReviewUpdate,
)
from app.services.audit import record_audit
from app.services import reviews as review_service
from app.utils.errors import NotFoundError, PermissionDeniedError, ValidationError

router = APIRouter()


def _build_out(r: Review) -> ReviewOut:
    """Convert a Review ORM instance to the response schema."""
    emp = r.employee
    cycle = r.cycle
    return ReviewOut(
        id=r.id,
        cycle_id=r.cycle_id,
        cycle_name=cycle.name if cycle else "Unknown",
        cycle_status=cycle.status if cycle else "unknown",
        employee_id=r.employee_id,
        employee_name=emp.full_name if emp else "Unknown",
        employee_position=emp.position if emp else None,
        employee_department=emp.department if emp else None,
        reviewer_user_id=r.reviewer_user_id,
        reviewer_name=r.reviewer.email if r.reviewer else None,
        rating=r.rating,
        strengths=r.strengths,
        improvements=r.improvements,
        goals=r.goals,
        status=r.status,
        submitted_at=r.submitted_at,
        shared_at=r.shared_at,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


async def _get_cycle(db: AsyncSession, cycle_id: int) -> ReviewCycle:
    cycle = await db.get(ReviewCycle, cycle_id)
    if not cycle:
        raise NotFoundError("Review cycle not found")
    return cycle


def _cycle_out(cycle: ReviewCycle) -> ReviewCycleOut:
    reviews = cycle.reviews
    return ReviewCycleOut(
        id=cycle.id,
        name=cycle.name,
        period_start=cycle.period_start,
        period_end=cycle.period_end,
        status=cycle.status,
        description=cycle.description,
        created_at=cycle.created_at,
        total_reviews=len(reviews),
        drafts=sum(1 for r in reviews if r.status == "draft"),
        submitted=sum(1 for r in reviews if r.status == "submitted"),
        shared=sum(1 for r in reviews if r.status == "shared"),
    )


# ── cycles ───────────────────────────────────────────────────────────────────


@router.get("/review-cycles/", response_model=list[ReviewCycleOut])
async def api_list_review_cycles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """All review cycles with live progress counts (newest period first)."""
    result = await db.execute(
        select(ReviewCycle).order_by(ReviewCycle.period_start.desc())
    )
    return [_cycle_out(c) for c in result.scalars().all()]


@router.post(
    "/review-cycles/",
    response_model=ReviewCycleOut,
    status_code=status.HTTP_201_CREATED,
)
async def api_create_review_cycle(
    data: ReviewCycleCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Create a review cycle (admin only)."""
    exists = (
        await db.execute(
            select(ReviewCycle.id).where(ReviewCycle.name == data.name)
        )
    ).scalar_one_or_none()
    if exists:
        raise ValidationError(f"A review cycle named '{data.name}' already exists")

    cycle = ReviewCycle(
        name=data.name,
        period_start=data.period_start,
        period_end=data.period_end,
        description=data.description,
    )
    db.add(cycle)
    await db.commit()
    await db.refresh(cycle)
    await record_audit(
        db,
        user=current_user,
        request=request,
        action="review_cycle.created",
        entity="review_cycle",
        entity_id=cycle.id,
        changes={"new": data.model_dump(mode="json")},
    )
    return _cycle_out(cycle)


# ── reviews ──────────────────────────────────────────────────────────────────


@router.get("/review-cycles/{cycle_id}/reviews/", response_model=list[ReviewOut])
async def api_list_cycle_reviews(
    cycle_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reviews in a cycle, scoped by role.

    Admins: everything. Managers: their direct reports. Employees: their own.
    """
    cycle = await _get_cycle(db, cycle_id)

    if current_user.role == UserRole.ADMIN:
        return [_build_out(r) for r in cycle.reviews]
    if current_user.role == UserRole.MANAGER:
        report_ids = await review_service.direct_report_ids(db, current_user)
        return [
            _build_out(r) for r in cycle.reviews if r.employee_id in report_ids
        ]
    emp_id = await review_service.my_employee_id(db, current_user)
    return [_build_out(r) for r in cycle.reviews if r.employee_id == emp_id]


@router.post(
    "/review-cycles/{cycle_id}/reviews/",
    response_model=ReviewOut,
    status_code=status.HTTP_201_CREATED,
)
async def api_create_review(
    cycle_id: int,
    data: ReviewCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Write a review for an employee (manager for direct reports, admin for anyone)."""
    cycle = await _get_cycle(db, cycle_id)
    if cycle.status == "closed":
        raise ValidationError("This review cycle is closed")

    employee = await db.get(Employee, data.employee_id)
    if not employee:
        raise NotFoundError("Employee not found")

    if not await review_service.can_review_employee(db, current_user, employee):
        raise PermissionDeniedError("You can only review your direct reports")

    existing = (
        await db.execute(
            select(Review.id).where(
                Review.cycle_id == cycle.id, Review.employee_id == employee.id
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise ValidationError("A review for this employee already exists in this cycle")

    now = datetime.now(timezone.utc)
    review = Review(
        cycle_id=cycle.id,
        employee_id=employee.id,
        reviewer_user_id=current_user.id,
        rating=data.rating,
        strengths=data.strengths,
        improvements=data.improvements,
        goals=data.goals,
        status="submitted" if data.submit else "draft",
        submitted_at=now if data.submit else None,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    await record_audit(
        db,
        user=current_user,
        request=request,
        action="review.created",
        entity="review",
        entity_id=review.id,
        changes={"new": data.model_dump(mode="json")},
    )
    return _build_out(review)


@router.get("/reviews/{review_id}", response_model=ReviewOut)
async def api_get_review(
    review_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single review (404 when the caller may not see it)."""
    review = await db.get(Review, review_id)
    if not review or not await review_service.can_view_review(db, current_user, review):
        raise NotFoundError("Review not found")
    return _build_out(review)


@router.patch("/reviews/{review_id}", response_model=ReviewOut)
async def api_update_review(
    review_id: int,
    data: ReviewUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Edit a review or move it between draft/submitted (author or admin)."""
    review = await db.get(Review, review_id)
    if not review or not await review_service.can_modify_review(db, current_user, review):
        raise NotFoundError("Review not found")
    if review.status == "shared":
        raise ValidationError("This review has been shared and can no longer be edited")

    old = {"status": review.status}
    provided = data.model_fields_set
    if "rating" in provided:
        review.rating = data.rating
    if "strengths" in provided:
        review.strengths = data.strengths
    if "improvements" in provided:
        review.improvements = data.improvements
    if "goals" in provided:
        review.goals = data.goals
    if "status" in provided:
        if data.status == "submitted" and review.status == "draft":
            review.submitted_at = datetime.now(timezone.utc)
        review.status = data.status

    await db.commit()
    await db.refresh(review)
    await record_audit(
        db,
        user=current_user,
        request=request,
        action="review.updated",
        entity="review",
        entity_id=review.id,
        changes={"old": old, "new": {"status": review.status}},
    )
    return _build_out(review)


@router.post("/reviews/{review_id}/share", response_model=ReviewOut)
async def api_share_review(
    review_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Share a submitted review with the employee and notify them (author or admin)."""
    review = await db.get(Review, review_id)
    if not review or not await review_service.can_modify_review(db, current_user, review):
        raise NotFoundError("Review not found")
    if review.status == "shared":
        raise ValidationError("This review has already been shared")
    if review.status != "submitted":
        raise ValidationError("Submit the review before sharing it")

    review.status = "shared"
    review.shared_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(review)

    cycle = await _get_cycle(db, review.cycle_id)
    await review_service.notify_review_shared(db, review, cycle)
    await record_audit(
        db,
        user=current_user,
        request=request,
        action="review.shared",
        entity="review",
        entity_id=review.id,
        changes={"old": {"status": "submitted"}, "new": {"status": "shared"}},
    )
    return _build_out(review)
