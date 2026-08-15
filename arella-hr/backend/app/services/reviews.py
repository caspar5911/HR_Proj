"""Performance review access control + notifications.

Visibility rules (mirror the leave-request scoping):

* **Admins** see and manage every review.
* **Managers** see and manage reviews for their direct reports only.
* **Employees** see only reviews about themselves.

Sharing a review notifies the employee through the in-app notification
service, which already skips recipients without a login account.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.review import Review, ReviewCycle
from app.models.user import User, UserRole
from app.services.notifications import notify_user
from app.utils.errors import PermissionDeniedError

logger = logging.getLogger(__name__)


async def my_employee_id(db: AsyncSession, user: User) -> int:
    """Resolve the Employee.id backing a user's login account.

    Raises :class:`PermissionDeniedError` when the account has no employee
    profile (same policy as the leave-request endpoints).
    """
    result = await db.execute(select(Employee.id).where(Employee.user_id == user.id))
    emp_id = result.scalar_one_or_none()
    if emp_id is None:
        raise PermissionDeniedError("No employee profile found for your account")
    return emp_id


async def _profile_ids(db: AsyncSession, user: User) -> set[int]:
    """Employee profile ID(s) backing a user's login account (usually one)."""
    result = await db.execute(select(Employee.id).where(Employee.user_id == user.id))
    return {row for (row,) in result.all()}


async def direct_report_ids(db: AsyncSession, user: User) -> set[int]:
    """Employee IDs that a manager user directly manages.

    Managers without an employee profile manage nobody (empty set).
    """
    if user.role != UserRole.MANAGER:
        return set()
    profile_ids = await _profile_ids(db, user)
    if not profile_ids:
        return set()
    result = await db.execute(
        select(Employee.id).where(Employee.manager_id.in_(profile_ids))
    )
    return {row for (row,) in result.all()}


async def can_view_review(db: AsyncSession, user: User, review: Review) -> bool:
    """Admins see all; managers their direct reports; employees their own."""
    if user.role == UserRole.ADMIN:
        return True
    if user.role == UserRole.MANAGER:
        return review.employee_id in await direct_report_ids(db, user)
    return review.employee_id == await my_employee_id(db, user)


async def can_modify_review(db: AsyncSession, user: User, review: Review) -> bool:
    """The original reviewer (or any admin) may edit or share a review."""
    if user.role == UserRole.ADMIN:
        return True
    return review.reviewer_user_id == user.id


async def can_review_employee(db: AsyncSession, user: User, employee: Employee) -> bool:
    """Admins may review anyone; managers only their direct reports."""
    if user.role == UserRole.ADMIN:
        return True
    if user.role == UserRole.MANAGER:
        return employee.manager_id in await _profile_ids(db, user)
    raise PermissionDeniedError("Only managers or admins can write reviews")


async def notify_review_shared(db: AsyncSession, review: Review, cycle: ReviewCycle) -> None:
    """Bell the employee that their review is ready to read."""
    result = await db.execute(
        select(Employee.user_id).where(
            Employee.id == review.employee_id, Employee.user_id.is_not(None)
        )
    )
    user_ids = [row for (row,) in result.all() if row is not None]
    if not user_ids:
        logger.warning("No user account for employee %s; skipping review notification", review.employee_id)
        return

    for user_id in user_ids:
        await notify_user(
            db,
            user_id=user_id,
            type="review_shared",
            title=f"{cycle.name} — your review is ready",
            body=f"Your manager shared your {cycle.name} review. Open My Reviews to view it.",
            link="/my-reviews",
        )
