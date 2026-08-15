"""In-app notification service.

Complements :mod:`app.services.email`: the same event that emails a manager
or employee also drops a bell entry they can open in the app. Recipients are
resolved through the Employee.user_id link, so only people with a login
account are notified.

The service is deliberately forgiving: a notification failure must never
break the primary operation that triggered it (e.g. approving a leave
request). Every public helper swallows its own errors and logs them.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.notification import Notification
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


# ── core writer ──────────────────────────────────────────────────────────────


async def notify_user(
    db: AsyncSession,
    *,
    user_id: int,
    type: str,
    title: str,
    body: str,
    link: str | None = None,
) -> Notification | None:
    """Create one notification for a user. Never raises.

    Returns the persisted :class:`Notification`, or ``None`` if writing
    failed.
    """
    try:
        notification = Notification(
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            link=link,
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        return notification
    except Exception:
        # Never let a notification failure take down the request; roll back
        # any partial transaction state and swallow (same policy as audit).
        logger.exception("Failed to create notification for user %s (%s)", user_id, type)
        try:
            await db.rollback()
        except Exception:
            pass
        return None


# ── recipient resolution ─────────────────────────────────────────────────────


async def _user_ids_for_employee(db: AsyncSession, employee_id: int) -> list[int]:
    """User account IDs backing a given employee profile."""
    result = await db.execute(
        select(Employee.user_id).where(Employee.id == employee_id, Employee.user_id.is_not(None))
    )
    return [row for (row,) in result.all() if row is not None]


async def _manager_user_ids(db: AsyncSession, employee: Employee) -> list[int]:
    """Recipients for a new-leave-request notification.

    The employee's direct manager (via the manager profile's user account);
    falling back to all active managers and admins when no manager with a
    login account exists — so a request can't go unseen in small setups.
    """
    if employee.manager_id:
        ids = await _user_ids_for_employee(db, employee.manager_id)
        if ids:
            return ids
    result = await db.execute(
        select(User.id).where(
            User.role.in_([UserRole.MANAGER, UserRole.ADMIN]),
            User.is_active.is_(True),
        )
    )
    return [row for (row,) in result.all()]


# ── event notifications ──────────────────────────────────────────────────────


async def notify_leave_requested(db: AsyncSession, request, employee: Employee) -> None:
    """Bell the manager that a new leave request is awaiting review."""
    leave_type_name = request.leave_type.name if request.leave_type else "leave"
    recipients = await _manager_user_ids(db, employee)
    if not recipients:
        logger.warning("No manager account found for employee %s; skipping in-app leave notification", employee.id)
        return

    title = f"New leave request from {employee.full_name}"
    body = (
        f"{employee.full_name} has requested {leave_type_name} leave "
        f"({request.start_date} to {request.end_date}, {request.days_requested:g} days)."
    )
    if request.reason:
        body += f" Reason: {request.reason}"

    for user_id in recipients:
        await notify_user(
            db, user_id=user_id, type="leave_requested",
            title=title, body=body, link="/leave",
        )


async def notify_leave_decided(db: AsyncSession, request) -> None:
    """Bell the employee that their leave request was approved or rejected."""
    user_ids = await _user_ids_for_employee(db, request.employee_id)
    if not user_ids:
        logger.warning("No user account for employee %s; skipping in-app leave-decision notification", request.employee_id)
        return

    decision = "approved" if request.status == "approved" else "rejected"
    leave_type_name = request.leave_type.name if request.leave_type else "leave"
    body = (
        f"Your {leave_type_name} leave request ({request.start_date} to "
        f"{request.end_date}) has been {decision}."
    )
    if request.manager_note:
        body += f" Note: {request.manager_note}"

    for user_id in user_ids:
        await notify_user(
            db, user_id=user_id, type=f"leave_{decision}",
            title=f"Your leave request was {decision}", body=body, link="/leave",
        )


async def notify_payroll_processed(db: AsyncSession, payroll_run, entries) -> None:
    """Bell every employee whose payroll entry was just generated."""
    if not entries:
        return

    # One entry per employee (a run generates exactly one per active employee).
    by_employee: dict[int, object] = {}
    for entry in entries:
        by_employee[entry.employee_id] = entry

    result = await db.execute(
        select(Employee.id, Employee.user_id, Employee.first_name).where(
            Employee.id.in_(by_employee), Employee.user_id.is_not(None)
        )
    )
    for emp_id, user_id, first_name in result.all():
        entry = by_employee[emp_id]
        period = f"{payroll_run.period_start} to {payroll_run.period_end}"
        await notify_user(
            db,
            user_id=user_id,
            type="payroll_processed",
            title=f"Your payroll for {period} is ready",
            body=f"Your net pay for this period is {float(entry.net_pay):,.2f}. Open My Home to view your payslip.",
            link="/my-home",
        )
